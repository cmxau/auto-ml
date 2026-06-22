import io
import logging
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import auc, confusion_matrix, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    name="app.workers.training_worker.train_model_task",
)
def train_model_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.dataset import Dataset, DatasetVersion
    from app.models.job import Job
    from app.models.project import Project  # noqa: F401
    from app.models.training import Artifact, TrainingMetric, TrainingRun
    from app.services.storage_service import storage
    from app.services.training_service import (
        build_model,
        compute_classification_metrics,
        compute_regression_metrics,
        extract_feature_importance,
        prepare_features,
        serialize_model,
    )

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Training job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        training_run_id = input_data["training_run_id"]

        run = db.get(TrainingRun, training_run_id)
        if not run:
            raise ValueError(f"TrainingRun {training_run_id} not found")

        run.train_status = "running"
        run.start_time = datetime.now(timezone.utc)
        db.commit()

        # Load dataset from MinIO
        version = db.get(DatasetVersion, run.dataset_version_id)
        dataset = db.get(Dataset, version.dataset_id)
        content = storage.download_file(version.storage_uri)

        from app.services.storage_service import resolve_format
        fmt = resolve_format(version.storage_uri, dataset.file_format)
        if fmt == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif fmt == "xlsx":
            df = pd.read_excel(io.BytesIO(content))
        elif fmt == "json":
            df = pd.read_json(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported file format: {fmt}")

        target = run.selected_target_column
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found in dataset")

        # Prepare features
        X, y_raw = prepare_features(df, target)

        # Encode target for classification
        if run.task_type == "classification":
            le = LabelEncoder()
            y_enc = le.fit_transform(y_raw.astype(str))
        else:
            y_enc = y_raw.values.astype(float)

        # Train/test split (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_enc, test_size=0.2, random_state=42
        )

        # Build and train model — normalize model_type to snake_case
        raw_model_type = run.model_type or ""
        # Convert PascalCase/CamelCase to snake_case (e.g. "LinearRegression" → "linear_regression")
        normalized = re.sub(r'(?<!^)(?=[A-Z])', '_', raw_model_type).lower().replace(' ', '_')
        model_type_to_use = normalized if normalized != raw_model_type.lower() else raw_model_type
        hyperparams = run.hyperparameters_json or {}
        model = build_model(model_type_to_use, hyperparams)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Compute metrics
        if run.task_type == "classification":
            y_prob = None
            if hasattr(model, "predict_proba"):
                try:
                    y_prob = model.predict_proba(X_test)
                except Exception:
                    pass
            metrics = compute_classification_metrics(y_test, y_pred, y_prob)
            metric_group = "classification"
        else:
            metrics = compute_regression_metrics(y_test, y_pred)
            metric_group = "regression"

        # Confusion matrix + ROC (classification only)
        eval_metrics: dict = {}
        if run.task_type == "classification":
            cm = confusion_matrix(y_test, y_pred)
            classes = [str(c) for c in np.unique(y_test)]
            eval_metrics["confusion_matrix"] = {
                "matrix": cm.tolist(),
                "classes": classes,
            }
            if len(classes) == 2 and hasattr(model, "predict_proba"):
                try:
                    y_proba = model.predict_proba(X_test)[:, 1]
                    fpr, tpr, _ = roc_curve(y_test, y_proba)
                    roc_auc = auc(fpr, tpr)
                    eval_metrics["roc_curve"] = {
                        "fpr": fpr.tolist(),
                        "tpr": tpr.tolist(),
                        "auc": round(roc_auc, 4),
                    }
                except Exception as roc_exc:
                    logger.warning("ROC curve computation failed: %s", roc_exc)

        # Feature importance
        feature_importance = extract_feature_importance(model, list(X.columns))

        # Serialize and upload model
        model_bytes = serialize_model(model)
        model_key = (
            f"artifacts/{dataset.project_id}/models/{training_run_id}/model.joblib"
        )
        storage.upload_file(io.BytesIO(model_bytes), model_key, "application/octet-stream")

        # Create artifact record
        artifact = Artifact(
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            training_run_id=training_run_id,
            artifact_type="model_file",
            storage_uri=model_key,
            file_name="model.joblib",
            mime_type="application/octet-stream",
            size_bytes=len(model_bytes),
        )
        db.add(artifact)
        db.flush()

        # Insert normalized metric records
        for metric_name, metric_value in metrics.items():
            db.add(TrainingMetric(
                training_run_id=training_run_id,
                metric_name=metric_name,
                metric_value=float(metric_value),
                metric_group=metric_group,
            ))

        # Update training run
        run.artifact_id = artifact.id
        run.train_status = "succeeded"
        run.end_time = datetime.now(timezone.utc)
        run.feature_importance_json = feature_importance
        run.output_json = eval_metrics if eval_metrics else None

        job.status = "succeeded"
        job.progress_percent = 100.0
        job.output_json = {
            "training_run_id": training_run_id,
            "metrics": metrics,
        }
        db.commit()
        logger.info("Training job %s succeeded for run %s", job_id, training_run_id)

    except Exception as exc:
        logger.exception("Training job %s failed: %s", job_id, exc)
        if job is not None:
            if self.request.retries >= self.max_retries:
                job.status = "failed"
                job.error_message = str(exc)
                try:
                    input_data = job.input_json or {}
                    run_id = input_data.get("training_run_id")
                    if run_id:
                        from app.models.training import TrainingRun
                        failed_run = db.get(TrainingRun, run_id)
                        if failed_run:
                            failed_run.train_status = "failed"
                            failed_run.end_time = datetime.now(timezone.utc)
                            failed_run.error_message = str(exc)
                except Exception:
                    pass
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()

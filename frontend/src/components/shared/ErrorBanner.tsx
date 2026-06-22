interface Props {
  message: string;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
      <span className="text-red-500 mt-0.5 shrink-0">✕</span>
      <p className="text-sm text-red-700 flex-1">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-red-400 hover:text-red-600 shrink-0 text-lg leading-none"
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  );
}

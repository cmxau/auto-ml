"use client";
import React from "react";

interface State { hasError: boolean; message: string }

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  State
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Something went wrong: {this.state.message}
          <button
            className="ml-3 underline text-red-500"
            onClick={() => this.setState({ hasError: false, message: "" })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from '@/components/ui';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled UI error', error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div role="alert" className="m-6 card p-8 text-center">
          <h1 className="text-lg font-semibold text-navy">Something went wrong</h1>
          <p className="mt-2 text-sm text-slate-500">{this.state.error.message}</p>
          <Button className="mt-4" onClick={() => this.setState({ error: null })}>
            Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

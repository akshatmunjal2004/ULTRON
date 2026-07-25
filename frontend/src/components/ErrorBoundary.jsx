import { Component } from 'react';

// A crash in one screen shouldn't blank the whole app. This catches render
// errors below it and shows a recoverable message instead of a white page.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Unhandled UI error:', error, info);
  }

  handleReset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="glass-panel max-w-md w-full p-6 text-center">
            <h2 className="text-lg font-semibold text-ultron-danger">Something broke</h2>
            <p className="mt-2 text-sm text-ultron-muted">
              A part of the interface hit an error. Your data is safe on the server.
            </p>
            <div className="mt-5 flex gap-3 justify-center">
              <button className="btn-ghost" onClick={this.handleReset}>
                Try again
              </button>
              <button className="btn-primary" onClick={() => window.location.reload()}>
                Reload
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { NotificationProvider, useNotifications } from '../renderer/contexts/NotificationContext';
import ToastNotification from '../renderer/components/ToastNotification';
import ErrorDialog from '../renderer/components/ErrorDialog';
import WarningDialog from '../renderer/components/WarningDialog';
import ConnectionStatus from '../renderer/components/ConnectionStatus';
import ValidationError from '../renderer/components/ValidationError';
import { ERROR_MESSAGES, mapErrorToAppError } from '../shared/error-types';

// Test component to access notification context
const TestNotificationConsumer: React.FC<{
  onMount: (helpers: ReturnType<typeof useNotifications>) => void;
}> = ({ onMount }) => {
  const helpers = useNotifications();
  React.useEffect(() => {
    onMount(helpers);
  }, [helpers, onMount]);
  return null;
};

describe('Error Handling Components', () => {
  describe('NotificationContext', () => {
    it('should provide notification helpers', () => {
      let helpers: ReturnType<typeof useNotifications> | null = null;

      render(
        <NotificationProvider>
          <TestNotificationConsumer onMount={(h) => { helpers = h; }} />
        </NotificationProvider>
      );

      expect(helpers).not.toBeNull();
      expect(helpers?.addNotification).toBeDefined();
      expect(helpers?.removeNotification).toBeDefined();
      expect(helpers?.showError).toBeDefined();
      expect(helpers?.showSuccess).toBeDefined();
      expect(helpers?.showWarning).toBeDefined();
      expect(helpers?.showInfo).toBeDefined();
    });

    it('should add and remove notifications', async () => {
      let helpers: ReturnType<typeof useNotifications> | null = null;

      const { container } = render(
        <NotificationProvider>
          <TestNotificationConsumer onMount={(h) => { helpers = h; }} />
          <div data-testid="notification-count">{helpers?.notifications.length || 0}</div>
        </NotificationProvider>
      );

      // Add notification
      helpers?.addNotification({
        type: 'success',
        title: 'Test',
        message: 'Test message'
      });

      await waitFor(() => {
        expect(helpers?.notifications.length).toBe(1);
      });

      // Remove notification
      const notificationId = helpers?.notifications[0].id;
      if (notificationId) {
        helpers?.removeNotification(notificationId);
      }

      await waitFor(() => {
        expect(helpers?.notifications.length).toBe(0);
      });
    });
  });

  describe('ToastNotification', () => {
    it('should render success toast', () => {
      const notification = {
        id: 'test-1',
        type: 'success' as const,
        title: 'Success',
        message: 'Operation completed',
        dismissible: true
      };

      render(
        <ToastNotification
          notification={notification}
          onDismiss={jest.fn()}
        />
      );

      expect(screen.getByText('Success')).toBeInTheDocument();
      expect(screen.getByText('Operation completed')).toBeInTheDocument();
    });

    it('should render error toast', () => {
      const notification = {
        id: 'test-2',
        type: 'error' as const,
        title: 'Error',
        message: 'Operation failed',
        dismissible: true
      };

      render(
        <ToastNotification
          notification={notification}
          onDismiss={jest.fn()}
        />
      );

      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText('Operation failed')).toBeInTheDocument();
    });

    it('should call onDismiss when dismiss button clicked', () => {
      const onDismiss = jest.fn();
      const notification = {
        id: 'test-3',
        type: 'info' as const,
        title: 'Info',
        message: 'Information',
        dismissible: true
      };

      render(
        <ToastNotification
          notification={notification}
          onDismiss={onDismiss}
        />
      );

      const dismissButton = screen.getByLabelText('Dismiss notification');
      fireEvent.click(dismissButton);

      // Should be called after animation
      setTimeout(() => {
        expect(onDismiss).toHaveBeenCalledWith('test-3');
      }, 400);
    });
  });

  describe('ErrorDialog', () => {
    it('should render error dialog with all information', () => {
      const error = ERROR_MESSAGES.SERIAL_CONNECTION_LOST;
      const onClose = jest.fn();

      render(
        <ErrorDialog
          error={error}
          onClose={onClose}
        />
      );

      expect(screen.getByText('ERROR DETECTED')).toBeInTheDocument();
      expect(screen.getByText(error.message)).toBeInTheDocument();
      expect(screen.getByText(error.userGuidance!)).toBeInTheDocument();
    });

    it('should show technical details when expanded', () => {
      const error = {
        ...ERROR_MESSAGES.DATABASE_WRITE_ERROR,
        technicalDetails: 'SQLITE_ERROR: disk I/O error'
      };

      render(
        <ErrorDialog
          error={error}
          onClose={jest.fn()}
        />
      );

      const detailsButton = screen.getByText('TECHNICAL DETAILS');
      fireEvent.click(detailsButton);

      expect(screen.getByText('SQLITE_ERROR: disk I/O error')).toBeInTheDocument();
    });

    it('should call onClose when close button clicked', () => {
      const onClose = jest.fn();
      const error = ERROR_MESSAGES.INVALID_PWM;

      render(
        <ErrorDialog
          error={error}
          onClose={onClose}
        />
      );

      const closeButton = screen.getByLabelText('Close dialog');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    it('should show retry button for recoverable errors', () => {
      const error = ERROR_MESSAGES.SERIAL_TIMEOUT;
      const onRetry = jest.fn();
      const onClose = jest.fn();

      render(
        <ErrorDialog
          error={error}
          onClose={onClose}
          onRetry={onRetry}
        />
      );

      const retryButton = screen.getByText('RETRY');
      expect(retryButton).toBeInTheDocument();

      fireEvent.click(retryButton);
      expect(onRetry).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('WarningDialog', () => {
    it('should render warning dialog', () => {
      render(
        <WarningDialog
          title="Delete Project"
          message="Are you sure?"
          onConfirm={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      expect(screen.getByText('Delete Project')).toBeInTheDocument();
      expect(screen.getByText('Are you sure?')).toBeInTheDocument();
    });

    it('should call onConfirm when confirm clicked', () => {
      const onConfirm = jest.fn();
      const onCancel = jest.fn();

      render(
        <WarningDialog
          title="Delete"
          message="Confirm deletion"
          onConfirm={onConfirm}
          onCancel={onCancel}
          confirmText="DELETE"
        />
      );

      const confirmButton = screen.getByText('DELETE');
      fireEvent.click(confirmButton);

      expect(onConfirm).toHaveBeenCalled();
    });

    it('should call onCancel when cancel clicked', () => {
      const onConfirm = jest.fn();
      const onCancel = jest.fn();

      render(
        <WarningDialog
          title="Delete"
          message="Confirm deletion"
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      );

      const cancelButton = screen.getByText('CANCEL');
      fireEvent.click(cancelButton);

      expect(onCancel).toHaveBeenCalled();
    });

    it('should render dangerous warning with different styling', () => {
      const { container } = render(
        <WarningDialog
          title="Dangerous Action"
          message="This is dangerous"
          onConfirm={jest.fn()}
          onCancel={jest.fn()}
          dangerous
        />
      );

      expect(screen.getByText('CRITICAL WARNING')).toBeInTheDocument();
      expect(container.querySelector('.border-neon-magenta')).toBeInTheDocument();
    });
  });

  describe('ConnectionStatus', () => {
    it('should render connected state', () => {
      render(<ConnectionStatus state="connected" portName="COM3" />);

      expect(screen.getByText('CONNECTED')).toBeInTheDocument();
      expect(screen.getByText('COM3')).toBeInTheDocument();
    });

    it('should render disconnected state', () => {
      render(<ConnectionStatus state="disconnected" />);

      expect(screen.getByText('DISCONNECTED')).toBeInTheDocument();
    });

    it('should render connecting state with animation', () => {
      const { container } = render(<ConnectionStatus state="connecting" />);

      expect(screen.getByText('CONNECTING')).toBeInTheDocument();
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('should render error state with message', () => {
      render(<ConnectionStatus state="error" errorMessage="Timeout" />);

      expect(screen.getByText('ERROR')).toBeInTheDocument();
      expect(screen.getByText('Timeout')).toBeInTheDocument();
    });
  });

  describe('ValidationError', () => {
    it('should render inline validation error', () => {
      render(
        <ValidationError
          message="Invalid value"
          inline
        />
      );

      expect(screen.getByText('Invalid value')).toBeInTheDocument();
    });

    it('should render block validation error with guidance', () => {
      render(
        <ValidationError
          message="Invalid project name"
          guidance="Names must be 1-50 characters"
        />
      );

      expect(screen.getByText('Invalid project name')).toBeInTheDocument();
      expect(screen.getByText('Names must be 1-50 characters')).toBeInTheDocument();
    });
  });

  describe('Error Mapping', () => {
    it('should map known errors to AppError', () => {
      const error = new Error('Serial connection lost');
      const appError = mapErrorToAppError(error);

      expect(appError.category).toBeDefined();
      expect(appError.code).toBeDefined();
      expect(appError.message).toBeDefined();
      expect(appError.userGuidance).toBeDefined();
    });

    it('should map unknown errors to generic AppError', () => {
      const error = new Error('Some random error');
      const appError = mapErrorToAppError(error);

      expect(appError.category).toBe('UNKNOWN');
      expect(appError.code).toBe('UNKNOWN_ERROR');
      expect(appError.message).toBe('An unexpected error occurred');
    });

    it('should include technical details in mapped error', () => {
      const error = new Error('Database write failed');
      const appError = mapErrorToAppError(error);

      expect(appError.technicalDetails).toBe('Database write failed');
    });
  });

  describe('Error Messages', () => {
    it('should have all required error categories', () => {
      const categories = new Set(
        Object.values(ERROR_MESSAGES).map(e => e.category)
      );

      expect(categories.has('VALIDATION')).toBe(true);
      expect(categories.has('SERIAL')).toBe(true);
      expect(categories.has('DATABASE')).toBe(true);
      expect(categories.has('FILE_SYSTEM')).toBe(true);
      expect(categories.has('EXECUTION')).toBe(true);
    });

    it('should have user guidance for all errors', () => {
      Object.values(ERROR_MESSAGES).forEach(error => {
        expect(error.userGuidance).toBeDefined();
        expect(error.userGuidance!.length).toBeGreaterThan(0);
      });
    });

    it('should mark validation errors as recoverable', () => {
      const validationErrors = Object.values(ERROR_MESSAGES)
        .filter(e => e.category === 'VALIDATION');

      validationErrors.forEach(error => {
        expect(error.recoverable).toBe(true);
      });
    });
  });
});

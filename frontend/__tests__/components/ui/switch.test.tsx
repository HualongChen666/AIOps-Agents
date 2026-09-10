import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Switch } from '@/components/ui/switch';

describe('Switch', () => {
  it('renders an accessible switch reflecting the checked state', () => {
    render(<Switch checked onCheckedChange={jest.fn()} />);
    const sw = screen.getByRole('switch');
    expect(sw).toHaveAttribute('aria-checked', 'true');
    expect(sw).toHaveClass('bg-blue-600');
  });

  it('renders the unchecked state with the neutral track color', () => {
    render(<Switch checked={false} onCheckedChange={jest.fn()} />);
    const sw = screen.getByRole('switch');
    expect(sw).toHaveAttribute('aria-checked', 'false');
    expect(sw).toHaveClass('bg-gray-200');
  });

  it('toggles by emitting the negated value on click', async () => {
    const user = userEvent.setup();
    const onCheckedChange = jest.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} />);

    await user.click(screen.getByRole('switch'));

    expect(onCheckedChange).toHaveBeenCalledTimes(1);
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it('emits false when toggling from checked', async () => {
    const user = userEvent.setup();
    const onCheckedChange = jest.fn();
    render(<Switch checked onCheckedChange={onCheckedChange} />);

    await user.click(screen.getByRole('switch'));

    expect(onCheckedChange).toHaveBeenCalledWith(false);
  });

  it('is inert and visually disabled when disabled', async () => {
    const user = userEvent.setup();
    const onCheckedChange = jest.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} disabled />);

    const sw = screen.getByRole('switch');
    expect(sw).toBeDisabled();
    expect(sw).toHaveClass('opacity-50');
    expect(sw).toHaveClass('cursor-not-allowed');

    await user.click(sw);
    expect(onCheckedChange).not.toHaveBeenCalled();
  });

  it('forwards id, name, aria-label and className to the button', () => {
    render(
      <Switch
        checked={false}
        onCheckedChange={jest.fn()}
        id="notify"
        name="notify-toggle"
        aria-label="Enable notifications"
        className="my-switch"
      />
    );
    const sw = screen.getByRole('switch');
    expect(sw).toHaveAttribute('id', 'notify');
    expect(sw).toHaveAttribute('name', 'notify-toggle');
    expect(sw).toHaveAttribute('aria-label', 'Enable notifications');
    expect(sw).toHaveClass('my-switch');
  });

  it('forwards aria-labelledby', () => {
    render(
      <Switch checked={false} onCheckedChange={jest.fn()} aria-labelledby="lbl-id" />
    );
    expect(screen.getByRole('switch')).toHaveAttribute('aria-labelledby', 'lbl-id');
  });

  it('moves the thumb according to the checked state', () => {
    const { rerender } = render(<Switch checked={false} onCheckedChange={jest.fn()} />);
    expect(document.querySelector('span')).toHaveClass('translate-x-1');

    rerender(<Switch checked onCheckedChange={jest.fn()} />);
    expect(document.querySelector('span')).toHaveClass('translate-x-6');
  });
});

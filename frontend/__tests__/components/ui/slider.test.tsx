import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Slider } from '@/components/ui/slider';

describe('Slider', () => {
  it('exposes min/max/value through the slider thumb ARIA attributes', () => {
    render(<Slider defaultValue={[50]} min={0} max={100} />);
    const thumb = screen.getByRole('slider');
    expect(thumb).toHaveAttribute('aria-valuemin', '0');
    expect(thumb).toHaveAttribute('aria-valuemax', '100');
    expect(thumb).toHaveAttribute('aria-valuenow', '50');
  });

  it('notifies onValueChange when moving with the keyboard', async () => {
    const user = userEvent.setup();
    const onValueChange = jest.fn();
    render(<Slider defaultValue={[50]} min={0} max={100} step={1} onValueChange={onValueChange} />);

    const thumb = screen.getByRole('slider');
    thumb.focus();
    await user.keyboard('{ArrowRight}');

    expect(onValueChange).toHaveBeenCalledWith([51]);
  });

  it('decrements with the left arrow key', async () => {
    const user = userEvent.setup();
    const onValueChange = jest.fn();
    render(<Slider defaultValue={[50]} min={0} max={100} step={1} onValueChange={onValueChange} />);

    const thumb = screen.getByRole('slider');
    thumb.focus();
    await user.keyboard('{ArrowLeft}');

    expect(onValueChange).toHaveBeenCalledWith([49]);
  });

  it('renders a single thumb (wrapper supports single-value sliders only)', () => {
    render(<Slider defaultValue={[20]} />);
    const thumbs = screen.getAllByRole('slider');
    expect(thumbs).toHaveLength(1);
    expect(thumbs[0]).toHaveAttribute('aria-valuenow', '20');
  });

  it('applies a custom className to the root', () => {
    const { container } = render(<Slider defaultValue={[10]} className="my-slider" />);
    expect(container.querySelector('[data-orientation]')).toHaveClass('my-slider');
  });

  it('supports a vertical orientation', () => {
    const { container } = render(<Slider defaultValue={[10]} orientation="vertical" />);
    expect(container.querySelector('[data-orientation="vertical"]')).toBeInTheDocument();
  });
});

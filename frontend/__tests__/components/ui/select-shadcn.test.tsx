import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectLabel,
  SelectSeparator,
} from '@/components/ui/select-shadcn';

const renderSelect = (props: { onValueChange?: (v: string) => void; disabled?: boolean } = {}) =>
  render(
    <Select onValueChange={props.onValueChange}>
      <SelectTrigger aria-label="Fruit" disabled={props.disabled}>
        <SelectValue placeholder="Choose a fruit" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>Citrus</SelectLabel>
          <SelectItem value="orange">Orange</SelectItem>
          <SelectItem value="lemon">Lemon</SelectItem>
        </SelectGroup>
        <SelectSeparator />
        <SelectItem value="apple">Apple</SelectItem>
      </SelectContent>
    </Select>
  );

describe('Select (shadcn wrapper)', () => {
  it('renders a closed combobox showing the placeholder', () => {
    renderSelect();
    expect(screen.getByRole('combobox', { name: 'Fruit' })).toBeInTheDocument();
    expect(screen.getByText('Choose a fruit')).toBeInTheDocument();
  });

  it('opens the listbox and shows grouped options', async () => {
    const user = userEvent.setup();
    renderSelect();

    await user.click(screen.getByRole('combobox', { name: 'Fruit' }));

    expect(await screen.findByRole('option', { name: 'Orange' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Lemon' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Apple' })).toBeInTheDocument();
    expect(screen.getByText('Citrus')).toBeInTheDocument();
  });

  it('selects an option and reports the value change', async () => {
    const user = userEvent.setup();
    const onValueChange = jest.fn();
    renderSelect({ onValueChange });

    await user.click(screen.getByRole('combobox', { name: 'Fruit' }));
    await user.click(await screen.findByRole('option', { name: 'Apple' }));

    expect(onValueChange).toHaveBeenCalledWith('apple');
    // The selected label replaces the placeholder in the trigger.
    expect(screen.getByRole('combobox', { name: 'Fruit' })).toHaveTextContent('Apple');
  });

  it('renders a disabled trigger that cannot be opened', async () => {
    const user = userEvent.setup();
    renderSelect({ disabled: true });

    const trigger = screen.getByRole('combobox', { name: 'Fruit' });
    expect(trigger).toBeDisabled();

    await user.click(trigger);
    expect(screen.queryByRole('option')).not.toBeInTheDocument();
  });
});

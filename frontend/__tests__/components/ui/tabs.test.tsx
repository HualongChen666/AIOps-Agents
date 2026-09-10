import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

const renderTabs = () =>
  render(
    <Tabs defaultValue="a">
      <TabsList>
        <TabsTrigger value="a">Tab A</TabsTrigger>
        <TabsTrigger value="b">Tab B</TabsTrigger>
      </TabsList>
      <TabsContent value="a">Content A</TabsContent>
      <TabsContent value="b">Content B</TabsContent>
    </Tabs>
  );

describe('Tabs', () => {
  it('renders the default tab content only', () => {
    renderTabs();
    expect(screen.getByText('Content A')).toBeInTheDocument();
    expect(screen.queryByText('Content B')).not.toBeInTheDocument();
  });

  it('switches the visible content when a trigger is clicked', async () => {
    const user = userEvent.setup();
    renderTabs();

    await user.click(screen.getByRole('tab', { name: 'Tab B' }));

    expect(screen.getByText('Content B')).toBeInTheDocument();
    expect(screen.queryByText('Content A')).not.toBeInTheDocument();
  });

  it('marks the active trigger with aria-selected', async () => {
    const user = userEvent.setup();
    renderTabs();

    expect(screen.getByRole('tab', { name: 'Tab A' })).toHaveAttribute('aria-selected', 'true');
    await user.click(screen.getByRole('tab', { name: 'Tab B' }));
    expect(screen.getByRole('tab', { name: 'Tab B' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Tab A' })).toHaveAttribute('aria-selected', 'false');
  });

  it('moves focus between tabs with the arrow keys', async () => {
    const user = userEvent.setup();
    renderTabs();

    screen.getByRole('tab', { name: 'Tab A' }).focus();
    await user.keyboard('{ArrowRight}');

    expect(screen.getByRole('tab', { name: 'Tab B' })).toHaveFocus();
  });

  it('applies className to the list, trigger and content', () => {
    render(
      <Tabs defaultValue="a">
        <TabsList className="list-x">
          <TabsTrigger value="a" className="trig-x">
            Only
          </TabsTrigger>
        </TabsList>
        <TabsContent value="a" className="cont-x">
          Body
        </TabsContent>
      </Tabs>
    );

    expect(screen.getByRole('tablist')).toHaveClass('list-x');
    expect(screen.getByRole('tab')).toHaveClass('trig-x');
    expect(screen.getByRole('tabpanel')).toHaveClass('cont-x');
  });

  it('renders a controlled tab set and reflects the external value', async () => {
    const onValueChange = jest.fn();
    render(
      <Tabs value="a" onValueChange={onValueChange}>
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
          <TabsTrigger value="b">Tab B</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
        <TabsContent value="b">Content B</TabsContent>
      </Tabs>
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: 'Tab B' }));
    expect(onValueChange).toHaveBeenCalledWith('b');
    // Controlled: value stays "a" until the parent updates it.
    expect(screen.getByText('Content A')).toBeInTheDocument();
  });
});

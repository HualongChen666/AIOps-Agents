import * as UI from '@/components/ui';
import { render, screen } from '@testing-library/react';
import React from 'react';

describe('components/ui barrel export', () => {
  it('re-exports every core UI primitive', () => {
    const expected = [
      'Card',
      'CardHeader',
      'CardTitle',
      'CardContent',
      'Button',
      'Badge',
      'Input',
      'Select',
      'Table',
      'TableHeader',
      'TableBody',
      'TableRow',
      'TableCell',
      'TableHead',
      'Textarea',
      'Dialog',
      'Progress',
      'Switch',
    ];
    for (const name of expected) {
      expect(UI[name as keyof typeof UI]).toBeDefined();
    }
  });

  it('exposes renderable components through the barrel', () => {
    const { Card, CardHeader, CardTitle, CardContent, Button, Badge } = UI;
    render(
      <Card>
        <CardHeader>
          <CardTitle>Barrel Card</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge>new</Badge>
          <Button>Go</Button>
        </CardContent>
      </Card>
    );

    expect(screen.getByText('Barrel Card')).toBeInTheDocument();
    expect(screen.getByText('new')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go' })).toBeInTheDocument();
  });
});

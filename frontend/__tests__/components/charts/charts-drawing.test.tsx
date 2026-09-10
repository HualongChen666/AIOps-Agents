import React from 'react';
import { render } from '@testing-library/react';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { ResourceTrendChart } from '@/components/charts/ResourceTrendChart';

/**
 * These tests assert the actual canvas drawing calls (jest.setup.js installs an
 * inert, cached 2D context stub, so `canvas.getContext('2d')` returns the same
 * spy object the component drew with).
 */
const ctxOf = (container: HTMLElement) => {
  const canvas = container.querySelector('canvas') as HTMLCanvasElement;
  return canvas.getContext('2d') as unknown as Record<string, jest.Mock>;
};

describe('chart canvas drawing', () => {
  describe('GaugeChart', () => {
    it('draws a background and a value arc at the computed centre/radius', () => {
      const { container } = render(<GaugeChart value={50} min={0} max={100} size={200} />);
      const ctx = ctxOf(container);

      // centre 100,100 ; radius = 200/2 - 20 = 80
      expect(ctx.arc).toHaveBeenCalledTimes(2);
      expect(ctx.arc.mock.calls[0].slice(0, 3)).toEqual([100, 100, 80]);
      // value arc spans half of the 270° sweep for value 50/100.
      const start = Math.PI * 0.75;
      expect(ctx.arc.mock.calls[1][3]).toBeCloseTo(start, 6);
      expect(ctx.arc.mock.calls[1][4]).toBeCloseTo(start + Math.PI * 1.5 * 0.5, 6);
    });

    it('writes the formatted value text and the title when provided', () => {
      const { container } = render(<GaugeChart value={72.34} unit="%" title="CPU" />);
      const ctx = ctxOf(container);

      expect(ctx.fillText).toHaveBeenCalledWith('72.3%', 100, 100);
      expect(ctx.fillText).toHaveBeenCalledWith('CPU', 100, 140);
    });

    it('clamps out-of-range values before drawing', () => {
      const { container } = render(<GaugeChart value={500} min={0} max={100} />);
      const ctx = ctxOf(container);
      expect(ctx.fillText).toHaveBeenCalledWith('100.0%', 100, 100);
    });

    it('omits the title draw when no title is given', () => {
      const { container } = render(<GaugeChart value={10} />);
      const ctx = ctxOf(container);
      const drawn = ctx.fillText.mock.calls.map((c) => c[0]);
      expect(drawn).toEqual(['10.0%']);
    });
  });

  describe('TrendChart', () => {
    it('draws 5 grid lines plus the line/area and one point per datum', () => {
      const { container } = render(
        <TrendChart data={[10, 20, 30]} labels={['a', 'b', 'c']} showGrid /> 
      );
      const ctx = ctxOf(container);

      // grid: 5 lines → 5 stroke calls before the data line; data line adds 1.
      expect(ctx.moveTo.mock.calls.length).toBeGreaterThanOrEqual(5 + 1);
      // 3 data points → 3 arcs.
      expect(ctx.arc).toHaveBeenCalledTimes(3);
      // labels are written.
      expect(ctx.fillText).toHaveBeenCalledWith('a', expect.any(Number), expect.any(Number));
    });

    it('skips the grid when showGrid is false', () => {
      const { container } = render(<TrendChart data={[10, 20, 30]} showGrid={false} />);
      const ctx = ctxOf(container);
      // Without grid there are no moveTo calls for grid rows; the data line still
      // calls moveTo once for its first point.
      expect(ctx.moveTo).toHaveBeenCalledTimes(1);
    });

    it('handles a single datum without dividing by zero', () => {
      const { container } = render(<TrendChart data={[42]} />);
      const ctx = ctxOf(container);
      expect(ctx.arc).toHaveBeenCalledTimes(1);
    });
  });

  describe('ResourceTrendChart', () => {
    it('scales for high DPI and draws three series plus the legend', () => {
      const data = [
        { timestamp: 't0', cpu: 50, memory: 60, disk: 70 },
        { timestamp: 't1', cpu: 55, memory: 65, disk: 75 },
      ];
      const { container } = render(<ResourceTrendChart data={data} />);
      const ctx = ctxOf(container);

      expect(ctx.scale).toHaveBeenCalledWith(2, 2);
      // three series each stroke once.
      expect(ctx.stroke.mock.calls.length).toBeGreaterThanOrEqual(3);
      const legend = ctx.fillText.mock.calls.map((c) => c[0]);
      expect(legend).toEqual(expect.arrayContaining(['CPU', '内存', '磁盘']));
    });

    it('draws nothing when the data array is empty', () => {
      const { container } = render(<ResourceTrendChart data={[]} />);
      const ctx = ctxOf(container);
      expect(ctx.scale).not.toHaveBeenCalled();
      expect(ctx.stroke).not.toHaveBeenCalled();
    });
  });
});

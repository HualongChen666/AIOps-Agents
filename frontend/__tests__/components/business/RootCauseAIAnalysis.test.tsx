import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RootCauseAIAnalysis } from '@/components/RootCauseAIAnalysis';

type Hypothesis = React.ComponentProps<typeof RootCauseAIAnalysis>['hypothesis'];

const makeHypothesis = (overrides: Partial<Hypothesis> = {}): Hypothesis => ({
  hypothesis_id: 'h-1',
  root_cause: '数据库连接池耗尽',
  confidence: 0.9,
  evidence: ['CPU 使用率飙升', '活跃连接数打满'],
  causal_path: ['慢查询', '连接堆积', '连接池耗尽'],
  impact_score: 0.75,
  verification_status: 'pending',
  verification_timestamp: null,
  recommended_action: 'auto_heal',
  requires_approval: false,
  expected_observations: ['P99 延迟下降'],
  missing_data: ['慢查询日志'],
  predicted_impact: { latency: 0.5, errorRate: 0.2 },
  is_multi_root: false,
  ...overrides,
});

describe('RootCauseAIAnalysis', () => {
  describe('main card', () => {
    it('renders the root cause, confidence percentage and label', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ confidence: 0.9 })} />);
      expect(screen.getByText('数据库连接池耗尽')).toBeInTheDocument();
      expect(screen.getByText('90.0%')).toHaveClass('bg-green-500');
      expect(screen.getByText('高置信度')).toBeInTheDocument();
    });

    it('maps confidence bands to labels and colors', () => {
      const { rerender } = render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ confidence: 0.7 })} />);
      expect(screen.getByText('中等置信度')).toBeInTheDocument();
      expect(screen.getByText('70.0%')).toHaveClass('bg-blue-500');

      rerender(
        <RootCauseAIAnalysis hypothesis={makeHypothesis({ confidence: 0.5, predicted_impact: {} })} />
      );
      expect(screen.getByText('低置信度')).toBeInTheDocument();
      expect(screen.getByText('50.0%')).toHaveClass('bg-yellow-500');

      rerender(<RootCauseAIAnalysis hypothesis={makeHypothesis({ confidence: 0.3 })} />);
      expect(screen.getByText('极低置信度')).toBeInTheDocument();
      expect(screen.getByText('30.0%')).toHaveClass('bg-red-500');
    });

    it('shows the multi-root badge only when flagged', () => {
      const { rerender } = render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} />);
      expect(screen.queryByText('多根因场景')).not.toBeInTheDocument();

      rerender(<RootCauseAIAnalysis hypothesis={makeHypothesis({ is_multi_root: true })} />);
      expect(screen.getByText('多根因场景')).toBeInTheDocument();
    });

    it('renders the impact score', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ impact_score: 0.42 })} />);
      expect(screen.getByText('0.42')).toBeInTheDocument();
    });
  });

  describe('recommended action', () => {
    it.each([
      ['auto_heal', '自动修复'],
      ['escalate', '升级处理'],
      ['collect_more_data', '收集更多数据'],
      ['do_something', 'do_something'],
    ])('labels %s as "%s"', (action, label) => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ recommended_action: action })} />);
      expect(screen.getByText(label)).toBeInTheDocument();
    });

    it('shows the approval badge when approval is required', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ requires_approval: true })} />);
      expect(screen.getByText('需要人工审批')).toBeInTheDocument();
    });
  });

  describe('verification status', () => {
    it.each([
      ['verified', '已验证'],
      ['partially_verified', '部分验证'],
      ['rejected', '已拒绝'],
      ['in_progress', '验证中'],
      ['unknown', '待验证'],
    ])('renders status %s as "%s"', (status, label) => {
      render(
        <RootCauseAIAnalysis
          hypothesis={makeHypothesis({ verification_status: status })}
          onVerify={jest.fn()}
        />
      );
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  describe('details section', () => {
    it('renders the causal path with separators', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} />);
      expect(screen.getByText('因果路径')).toBeInTheDocument();
      expect(screen.getByText('慢查询')).toBeInTheDocument();
      expect(screen.getByText('连接堆积')).toBeInTheDocument();
      expect(screen.getByText('连接池耗尽')).toBeInTheDocument();
      expect(screen.getAllByText('→')).toHaveLength(2);
    });

    it('renders evidence, expected observations and missing data', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} />);
      expect(screen.getByText('证据链')).toBeInTheDocument();
      expect(screen.getByText('CPU 使用率飙升')).toBeInTheDocument();
      expect(screen.getByText('预期观察')).toBeInTheDocument();
      expect(screen.getByText('P99 延迟下降')).toBeInTheDocument();
      expect(screen.getByText('缺失数据')).toBeInTheDocument();
      expect(screen.getByText('慢查询日志')).toBeInTheDocument();
    });

    it('renders predicted impact as percentages', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} />);
      expect(screen.getByText('latency')).toBeInTheDocument();
      expect(screen.getByText('50.0%')).toBeInTheDocument();
      expect(screen.getByText('errorRate')).toBeInTheDocument();
      expect(screen.getByText('20.0%')).toBeInTheDocument();
    });

    it('omits empty optional sections', () => {
      render(
        <RootCauseAIAnalysis
          hypothesis={makeHypothesis({
            causal_path: [],
            evidence: [],
            expected_observations: [],
            missing_data: [],
            predicted_impact: {},
          })}
        />
      );
      expect(screen.queryByText('因果路径')).not.toBeInTheDocument();
      expect(screen.queryByText('证据链')).not.toBeInTheDocument();
      expect(screen.queryByText('预期观察')).not.toBeInTheDocument();
      expect(screen.queryByText('缺失数据')).not.toBeInTheDocument();
      expect(screen.queryByText('预测影响')).not.toBeInTheDocument();
    });

    it('hides the details when showFullDetails is false', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} showFullDetails={false} />);
      expect(screen.getByText('数据库连接池耗尽')).toBeInTheDocument();
      expect(screen.queryByText('因果路径')).not.toBeInTheDocument();
      expect(screen.queryByText('验证假设')).not.toBeInTheDocument();
    });
  });

  describe('action buttons', () => {
    it('invokes onVerify with the hypothesis id', async () => {
      const user = userEvent.setup();
      const onVerify = jest.fn();
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis()} onVerify={onVerify} />);

      await user.click(screen.getByRole('button', { name: /验证假设/ }));

      expect(onVerify).toHaveBeenCalledWith('h-1');
    });

    it('disables the verify button when already verified', () => {
      render(
        <RootCauseAIAnalysis
          hypothesis={makeHypothesis({ verification_status: 'verified' })}
          onVerify={jest.fn()}
        />
      );
      expect(screen.getByRole('button', { name: /验证假设/ })).toBeDisabled();
    });

    it('only shows the approve button when approval is required', () => {
      const { rerender } = render(
        <RootCauseAIAnalysis hypothesis={makeHypothesis()} onApprove={jest.fn()} />
      );
      expect(screen.queryByRole('button', { name: /批准执行/ })).not.toBeInTheDocument();

      rerender(
        <RootCauseAIAnalysis
          hypothesis={makeHypothesis({ requires_approval: true })}
          onApprove={jest.fn()}
        />
      );
      expect(screen.getByRole('button', { name: /批准执行/ })).toBeInTheDocument();
    });

    it('invokes onApprove and onReject with the hypothesis id', async () => {
      const user = userEvent.setup();
      const onApprove = jest.fn();
      const onReject = jest.fn();
      render(
        <RootCauseAIAnalysis
          hypothesis={makeHypothesis({ requires_approval: true })}
          onApprove={onApprove}
          onReject={onReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /批准执行/ }));
      expect(onApprove).toHaveBeenCalledWith('h-1');

      await user.click(screen.getByRole('button', { name: /拒绝假设/ }));
      expect(onReject).toHaveBeenCalledWith('h-1');
    });

    it('renders no action buttons when no handlers are provided', () => {
      render(<RootCauseAIAnalysis hypothesis={makeHypothesis({ requires_approval: true })} />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });
});

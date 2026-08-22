import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AnomalyPage from '@/app/anomaly/page';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(() => 'test-token'),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve([]),
  })
) as jest.Mock;

describe('AnomalyPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Rendering', () => {
    it('should render the anomaly page with title', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('异常检测')).toBeInTheDocument();
    });

    it('should render refresh button', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('刷新数据')).toBeInTheDocument();
    });

    it('should render model selection card', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('检测模型')).toBeInTheDocument();
    });

    it('should render confidence threshold selector', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('置信度阈值 (%)')).toBeInTheDocument();
    });

    it('should render apply configuration button', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('应用配置')).toBeInTheDocument();
    });

    it('should render time series chart card', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('时序异常检测')).toBeInTheDocument();
    });

    it('should render anomaly records table', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('异常记录')).toBeInTheDocument();
    });

    it('should render model configuration card', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('模型配置')).toBeInTheDocument();
    });
  });

  describe('Model Selection', () => {
    it('should have prophet as default model', () => {
      render(<AnomalyPage />);

      const modelSelect = screen.getAllByRole('combobox')[0];
      expect(modelSelect).toHaveValue('prophet');
    });

    it('should change model selection', () => {
      render(<AnomalyPage />);

      const modelSelect = screen.getAllByRole('combobox')[0];
      fireEvent.change(modelSelect, { target: { value: 'isolation-forest' } });

      expect(modelSelect).toHaveValue('isolation-forest');
    });

    it('should have all model options', () => {
      render(<AnomalyPage />);

      const modelSelect = screen.getAllByRole('combobox')[0];
      const options = modelSelect.querySelectorAll('option');

      expect(options).toHaveLength(3);
      expect(options[0]).toHaveValue('prophet');
      expect(options[1]).toHaveValue('isolation-forest');
      expect(options[2]).toHaveValue('ensemble');
    });
  });

  describe('Confidence Threshold', () => {
    it('should have 95% as default confidence', () => {
      render(<AnomalyPage />);

      const confidenceSelect = screen.getAllByRole('combobox')[1];
      expect(confidenceSelect).toHaveValue('95');
    });

    it('should change confidence threshold', () => {
      render(<AnomalyPage />);

      const confidenceSelect = screen.getAllByRole('combobox')[1];
      fireEvent.change(confidenceSelect, { target: { value: '99' } });

      expect(confidenceSelect).toHaveValue('99');
    });

    it('should have all confidence options', () => {
      render(<AnomalyPage />);

      const confidenceSelect = screen.getAllByRole('combobox')[1];
      const options = confidenceSelect.querySelectorAll('option');

      expect(options).toHaveLength(3);
      expect(options[0]).toHaveValue('90');
      expect(options[1]).toHaveValue('95');
      expect(options[2]).toHaveValue('99');
    });
  });

  describe('Model Configuration', () => {
    it('should render sampling rate selector', () => {
      render(<AnomalyPage />);

      const selectElements = screen.getAllByRole('combobox');
      expect(selectElements.length).toBeGreaterThan(2);
    });

    it('should render history window selector', () => {
      render(<AnomalyPage />);

      const selectElements = screen.getAllByRole('combobox');
      expect(selectElements.length).toBeGreaterThan(3);
    });

    it('should render sensitivity selector', () => {
      render(<AnomalyPage />);

      const selectElements = screen.getAllByRole('combobox');
      expect(selectElements.length).toBeGreaterThan(4);
    });

    it('should render auto alert selector', () => {
      render(<AnomalyPage />);

      const selectElements = screen.getAllByRole('combobox');
      expect(selectElements.length).toBeGreaterThan(5);
    });

    it('should render save configuration button', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('保存配置')).toBeInTheDocument();
    });

    it('should have sampling rate options', () => {
      render(<AnomalyPage />);

      const samplingSelect = screen.getAllByRole('combobox')[2];
      const options = samplingSelect.querySelectorAll('option');

      expect(options).toHaveLength(4);
      expect(options[0]).toHaveValue('1s');
      expect(options[1]).toHaveValue('5s');
      expect(options[2]).toHaveValue('1m');
      expect(options[3]).toHaveValue('5m');
    });

    it('should have history window options', () => {
      render(<AnomalyPage />);

      const historySelect = screen.getAllByRole('combobox')[3];
      const options = historySelect.querySelectorAll('option');

      expect(options).toHaveLength(4);
      expect(options[0]).toHaveValue('1h');
      expect(options[1]).toHaveValue('24h');
      expect(options[2]).toHaveValue('7d');
      expect(options[3]).toHaveValue('30d');
    });

    it('should have sensitivity options', () => {
      render(<AnomalyPage />);

      const sensitivitySelect = screen.getAllByRole('combobox')[4];
      const options = sensitivitySelect.querySelectorAll('option');

      expect(options).toHaveLength(3);
      expect(options[0]).toHaveValue('low');
      expect(options[1]).toHaveValue('medium');
      expect(options[2]).toHaveValue('high');
    });

    it('should have auto alert options', () => {
      render(<AnomalyPage />);

      const autoAlertSelect = screen.getAllByRole('combobox')[5];
      const options = autoAlertSelect.querySelectorAll('option');

      expect(options).toHaveLength(2);
      expect(options[0]).toHaveValue('enabled');
      expect(options[1]).toHaveValue('disabled');
    });
  });

  describe('Time Series Chart', () => {
    it('should display chart area', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('时序图表区域')).toBeInTheDocument();
    });

    it('should display chart legend badges', () => {
      render(<AnomalyPage />);

      expect(screen.getAllByText('实际值').length).toBeGreaterThan(0);
      expect(screen.getAllByText('预测值').length).toBeGreaterThan(0);
      expect(screen.getAllByText('置信区间').length).toBeGreaterThan(0);
      expect(screen.getAllByText('异常点').length).toBeGreaterThan(0);
    });
  });

  describe('Refresh Functionality', () => {
    it('should refresh data when refresh button is clicked', () => {
      render(<AnomalyPage />);

      const refreshButton = screen.getByText('刷新数据');
      fireEvent.click(refreshButton);

      expect(screen.getByText('异常检测')).toBeInTheDocument();
    });
  });

  describe('Table Headers', () => {
    it('should display all table headers', () => {
      render(<AnomalyPage />);

      expect(screen.getByText('ID')).toBeInTheDocument();
      expect(screen.getByText('时间')).toBeInTheDocument();
      expect(screen.getByText('指标')).toBeInTheDocument();
      expect(screen.getAllByText('实际值').length).toBeGreaterThan(0);
      expect(screen.getAllByText('预测值').length).toBeGreaterThan(0);
      expect(screen.getByText('偏差')).toBeInTheDocument();
      expect(screen.getByText('置信度')).toBeInTheDocument();
      expect(screen.getByText('操作')).toBeInTheDocument();
    });
  });

  describe('Apply Configuration', () => {
    it('should handle apply configuration button click', () => {
      render(<AnomalyPage />);

      const applyButton = screen.getByText('应用配置');
      fireEvent.click(applyButton);

      expect(screen.getByText('应用配置')).toBeInTheDocument();
    });
  });

  describe('Save Configuration', () => {
    it('should handle save configuration button click', () => {
      render(<AnomalyPage />);

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(screen.getByText('保存配置')).toBeInTheDocument();
    });
  });

  describe('Auth Token Handling', () => {
    it('should handle missing auth token', () => {
      localStorageMock.getItem.mockReturnValue(null);

      render(<AnomalyPage />);

      expect(screen.getByText('异常检测')).toBeInTheDocument();
    });
  });

  describe('Configuration Changes', () => {
    it('should change sampling rate', () => {
      render(<AnomalyPage />);

      const samplingSelect = screen.getAllByRole('combobox')[2];
      fireEvent.change(samplingSelect, { target: { value: '5s' } });

      expect(samplingSelect).toHaveValue('5s');
    });

    it('should change history window', () => {
      render(<AnomalyPage />);

      const historySelect = screen.getAllByRole('combobox')[3];
      fireEvent.change(historySelect, { target: { value: '24h' } });

      expect(historySelect).toHaveValue('24h');
    });

    it('should change sensitivity', () => {
      render(<AnomalyPage />);

      const sensitivitySelect = screen.getAllByRole('combobox')[4];
      fireEvent.change(sensitivitySelect, { target: { value: 'high' } });

      expect(sensitivitySelect).toHaveValue('high');
    });

    it('should change auto alert setting', () => {
      render(<AnomalyPage />);

      const autoAlertSelect = screen.getAllByRole('combobox')[5];
      fireEvent.change(autoAlertSelect, { target: { value: 'disabled' } });

      expect(autoAlertSelect).toHaveValue('disabled');
    });
  });
});

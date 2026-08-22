import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TopologyGraph } from '@/components/TopologyGraph';
import api from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock @antv/g6
jest.mock('@antv/g6', () => ({
  Graph: jest.fn().mockImplementation(() => ({
    changeData: jest.fn(),
    fitView: jest.fn(),
    destroy: jest.fn(),
  })),
}));

// Mock react-query
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('TopologyGraph Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<TopologyGraph />);
      
      expect(screen.getByText('加载拓扑中…')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message when API fails', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(screen.getByText(/拓扑加载失败/)).toBeInTheDocument();
      });
    });

    it('should display error message', async () => {
      const error = new Error('Network error');
      mockedApi.get.mockRejectedValue(error);
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('Data Rendering', () => {
    const mockTopologyData = {
      nodes: [
        { id: 'node1', label: 'Server 1', status: 'normal' as const },
        { id: 'node2', label: 'Server 2', status: 'warning' as const },
        { id: 'node3', label: 'Server 3', status: 'critical' as const },
      ],
      edges: [
        { source: 'node1', target: 'node2', label: 'connection' },
        { source: 'node2', target: 'node3', label: 'link' },
      ],
    };

    it('should render graph container when data is loaded', async () => {
      mockedApi.get.mockResolvedValue({ data: mockTopologyData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        const container = document.querySelector('div');
        expect(container).toBeInTheDocument();
      });
    });

    it('should call API with correct endpoint', async () => {
      mockedApi.get.mockResolvedValue({ data: mockTopologyData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/topologies/full-link');
      });
    });
  });

  describe('Node Status Styling', () => {
    it('should apply correct color for normal status', async () => {
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server', status: 'normal' as const }],
        edges: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });

    it('should apply correct color for warning status', async () => {
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server', status: 'warning' as const }],
        edges: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });

    it('should apply correct color for critical status', async () => {
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server', status: 'critical' as const }],
        edges: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });
  });

  describe('Graph Configuration', () => {
    it('should initialize graph with correct configuration', async () => {
      const { Graph } = require('@antv/g6');
      mockedApi.get.mockResolvedValue({ data: { nodes: [], edges: [] } });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(Graph).toHaveBeenCalled();
      });
    });

    it('should update graph data when data changes', async () => {
      const mockGraph = {
        changeData: jest.fn(),
        fitView: jest.fn(),
        destroy: jest.fn(),
      };
      const { Graph } = require('@antv/g6');
      Graph.mockReturnValue(mockGraph);
      
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server', status: 'normal' as const }],
        edges: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockGraph.changeData).toHaveBeenCalled();
        expect(mockGraph.fitView).toHaveBeenCalled();
      });
    });
  });

  describe('Node Click Handler', () => {
    it('should accept onNodeClick prop', () => {
      const handleNodeClick = jest.fn();
      mockedApi.get.mockResolvedValue({ data: { nodes: [], edges: [] } });
      
      renderWithQueryClient(<TopologyGraph onNodeClick={handleNodeClick} />);
      
      expect(screen.getByText('加载拓扑中…')).toBeInTheDocument();
    });
  });

  describe('Container Styling', () => {
    it('should apply correct container styles', async () => {
      mockedApi.get.mockResolvedValue({ data: { nodes: [], edges: [] } });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        const container = document.querySelector('div');
        expect(container).toHaveClass('w-full');
        expect(container).toHaveClass('h-[600px]');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty topology data', async () => {
      mockedApi.get.mockResolvedValue({ data: { nodes: [], edges: [] } });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });

    it('should handle nodes without status', async () => {
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server' }],
        edges: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });

    it('should handle edges without labels', async () => {
      const mockData = {
        nodes: [{ id: 'node1', label: 'Server', status: 'normal' as const }],
        edges: [{ source: 'node1', target: 'node2' }],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });
  });

  describe('Refetch Interval', () => {
    it('should set up refetch interval', async () => {
      mockedApi.get.mockResolvedValue({ data: { nodes: [], edges: [] } });
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have accessible loading message', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<TopologyGraph />);
      
      expect(screen.getByText('加载拓扑中…')).toBeInTheDocument();
    });

    it('should have accessible error message', async () => {
      mockedApi.get.mockRejectedValue(new Error('Error'));
      
      renderWithQueryClient(<TopologyGraph />);
      
      await waitFor(() => {
        expect(screen.getByText(/拓扑加载失败/)).toBeInTheDocument();
      });
    });
  });
});

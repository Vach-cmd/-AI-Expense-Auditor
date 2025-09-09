import React from 'react';
import { useQuery } from 'react-query';
import { apiClient } from '../api/client';
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  TrendingUp,
  DollarSign
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const { data: dashboardData, isLoading, error } = useQuery(
    'dashboard',
    () => apiClient.get('/analytics/dashboard'),
    {
      refetchInterval: 30000, // Refetch every 30 seconds
    }
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-700">Failed to load dashboard data</div>
      </div>
    );
  }

  const stats = dashboardData?.statistics || {};
  const recentInvoices = dashboardData?.recent_invoices || [];

  const statCards = [
    {
      name: 'Total Invoices',
      value: stats.total_invoices || 0,
      icon: FileText,
      color: 'blue',
    },
    {
      name: 'Processed',
      value: stats.processed_invoices || 0,
      icon: CheckCircle,
      color: 'green',
    },
    {
      name: 'Pending',
      value: stats.pending_invoices || 0,
      icon: Clock,
      color: 'yellow',
    },
    {
      name: 'Fraud Detected',
      value: stats.fraud_detected || 0,
      icon: AlertTriangle,
      color: 'red',
    },
  ];

  const getColorClasses = (color: string) => {
    const colors = {
      blue: 'bg-blue-500 text-white',
      green: 'bg-green-500 text-white',
      yellow: 'bg-yellow-500 text-white',
      red: 'bg-red-500 text-white',
    };
    return colors[color as keyof typeof colors] || colors.blue;
  };

  const getRiskBadgeColor = (score: number) => {
    if (score > 0.8) return 'badge-danger';
    if (score > 0.5) return 'badge-warning';
    return 'badge-success';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your expense audit system</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card">
              <div className="flex items-center">
                <div className={`p-3 rounded-lg ${getColorClasses(stat.color)}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Processing Rate */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Processing Metrics</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Processing Rate</span>
              <span className="text-sm font-medium text-gray-900">
                {((stats.processing_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${(stats.processing_rate || 0) * 100}%` }}
              ></div>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Fraud Rate</span>
              <span className="text-sm font-medium text-gray-900">
                {((stats.fraud_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-red-600 h-2 rounded-full"
                style={{ width: `${(stats.fraud_rate || 0) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {recentInvoices.slice(0, 5).map((invoice: any) => (
              <div key={invoice.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {invoice.vendor_name || 'Unknown Vendor'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {invoice.invoice_number || `#${invoice.id}`}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">
                    ${invoice.total_amount || invoice.amount || 0}
                  </span>
                  <span className={`badge ${getRiskBadgeColor(invoice.fraud_score || 0)}`}>
                    {invoice.fraud_score ? (invoice.fraud_score * 100).toFixed(0) : 0}%
                  </span>
                </div>
              </div>
            ))}
            {recentInvoices.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">
                No recent invoices
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

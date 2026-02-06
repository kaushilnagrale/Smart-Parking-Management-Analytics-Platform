import { useState, useEffect } from 'react';
import { analyticsAPI, zonesAPI } from '../services/api';
import { useParkingWebSocket } from '../hooks/useWebSocket';
import StatsCards from '../components/dashboard/StatsCards';
import ZoneGrid from '../components/parking/ZoneGrid';
import OccupancyChart from '../components/dashboard/OccupancyChart';
import RecentEvents from '../components/dashboard/RecentEvents';
import { RefreshCw, Wifi, WifiOff } from 'lucide-react';

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isConnected, zoneUpdates, events } = useParkingWebSocket();

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const res = await analyticsAPI.getDashboard();
      setDashboard(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  // Merge WebSocket updates into dashboard zones
  const zones = dashboard?.zones?.map((zone) => {
    const update = zoneUpdates[zone.zone_code];
    if (update) {
      return {
        ...zone,
        occupied_spots: update.occupied_spots ?? zone.total_spots - zone.available_spots,
        available_spots: update.total_spots - (update.occupied_spots ?? 0),
        occupancy_rate: update.occupancy_rate ?? zone.occupancy_rate,
      };
    }
    return zone;
  }) || [];

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-parking-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time parking overview</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${
            isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? 'Live' : 'Offline'}
          </span>
          <button
            onClick={fetchDashboard}
            className="p-2 text-gray-500 hover:text-parking-600 hover:bg-gray-100 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Summary Stats */}
      {dashboard && <StatsCards dashboard={dashboard} />}

      {/* Zone Grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Parking Zones</h2>
        <ZoneGrid zones={zones} />
      </div>

      {/* Charts & Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OccupancyChart />
        <RecentEvents events={events} />
      </div>
    </div>
  );
}

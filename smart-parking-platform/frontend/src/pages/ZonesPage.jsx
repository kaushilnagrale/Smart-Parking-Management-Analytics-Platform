import { useState, useEffect } from 'react';
import { zonesAPI } from '../services/api';
import ZoneGrid from '../components/parking/ZoneGrid';
import { Plus, RefreshCw } from 'lucide-react';

export default function ZonesPage() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchZones = async () => {
    setLoading(true);
    try {
      const res = await zonesAPI.list(false);
      setZones(res.data);
    } catch (err) {
      console.error('Failed to fetch zones:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchZones(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Parking Zones</h1>
          <p className="text-gray-500 text-sm mt-1">{zones.length} zones configured</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchZones}
            className="p-2 text-gray-500 hover:text-parking-600 hover:bg-gray-100 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button className="inline-flex items-center gap-2 bg-parking-600 hover:bg-parking-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
            <Plus className="w-4 h-4" />
            Add Zone
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="w-6 h-6 text-parking-500 animate-spin" />
        </div>
      ) : (
        <ZoneGrid zones={zones.map((z) => ({
          zone_code: z.zone_code,
          zone_name: z.name,
          zone_type: z.zone_type,
          total_spots: z.total_spots,
          available_spots: z.available_spots,
          occupancy_rate: z.occupancy_rate,
        }))} />
      )}

      {/* Zone Detail Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Zone</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Type</th>
              <th className="text-left px-4 py-3 text-gray-500 font-medium">Floor</th>
              <th className="text-right px-4 py-3 text-gray-500 font-medium">Occupied</th>
              <th className="text-right px-4 py-3 text-gray-500 font-medium">Total</th>
              <th className="text-right px-4 py-3 text-gray-500 font-medium">Rate</th>
              <th className="text-right px-4 py-3 text-gray-500 font-medium">$/hr</th>
              <th className="text-center px-4 py-3 text-gray-500 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((z) => (
              <tr key={z.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className="font-medium text-gray-900">{z.zone_code}</span>
                  <span className="text-gray-400 ml-2 text-xs">{z.name}</span>
                </td>
                <td className="px-4 py-3 capitalize text-gray-600">{z.zone_type.replace('_', ' ')}</td>
                <td className="px-4 py-3 text-gray-600">{z.floor_level === 0 ? 'Ground' : z.floor_level > 0 ? `L${z.floor_level}` : `B${Math.abs(z.floor_level)}`}</td>
                <td className="px-4 py-3 text-right font-mono">{z.occupied_spots}</td>
                <td className="px-4 py-3 text-right font-mono">{z.total_spots}</td>
                <td className="px-4 py-3 text-right font-mono">{z.occupancy_rate.toFixed(1)}%</td>
                <td className="px-4 py-3 text-right font-mono">${z.hourly_rate.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                    z.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {z.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

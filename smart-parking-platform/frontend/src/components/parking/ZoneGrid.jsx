import { Car, Zap, Accessibility, Crown, Truck } from 'lucide-react';
import clsx from 'clsx';

const typeIcons = {
  standard: Car,
  compact: Car,
  handicap: Accessibility,
  ev_charging: Zap,
  vip: Crown,
  oversized: Truck,
};

const typeColors = {
  standard: 'border-blue-200 bg-blue-50',
  compact: 'border-cyan-200 bg-cyan-50',
  handicap: 'border-purple-200 bg-purple-50',
  ev_charging: 'border-green-200 bg-green-50',
  vip: 'border-amber-200 bg-amber-50',
  oversized: 'border-gray-200 bg-gray-50',
};

function getOccupancyColor(rate) {
  if (rate >= 90) return 'text-red-600';
  if (rate >= 70) return 'text-orange-500';
  if (rate >= 50) return 'text-yellow-500';
  return 'text-green-500';
}

function getBarColor(rate) {
  if (rate >= 90) return 'bg-red-500';
  if (rate >= 70) return 'bg-orange-400';
  if (rate >= 50) return 'bg-yellow-400';
  return 'bg-green-400';
}

export default function ZoneGrid({ zones = [] }) {
  if (zones.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">No zones available</div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {zones.map((zone) => {
        const Icon = typeIcons[zone.zone_type] || Car;
        const rate = zone.occupancy_rate;

        return (
          <div
            key={zone.zone_code}
            className={clsx(
              'rounded-xl border-2 p-4 hover:shadow-md transition cursor-pointer',
              typeColors[zone.zone_type] || 'border-gray-200 bg-gray-50'
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-gray-600" />
                <span className="font-bold text-gray-900">{zone.zone_code}</span>
              </div>
              <span className={clsx('text-lg font-bold', getOccupancyColor(rate))}>
                {rate.toFixed(0)}%
              </span>
            </div>

            <p className="text-xs text-gray-500 mb-3 truncate">{zone.zone_name}</p>

            {/* Occupancy bar */}
            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
              <div
                className={clsx('h-2 rounded-full transition-all duration-500', getBarColor(rate))}
                style={{ width: `${Math.min(rate, 100)}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-gray-500">
              <span>{zone.available_spots} available</span>
              <span>{zone.total_spots} total</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

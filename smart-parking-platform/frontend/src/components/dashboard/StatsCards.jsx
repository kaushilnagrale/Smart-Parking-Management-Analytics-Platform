import { Car, MapPin, Camera, Activity } from 'lucide-react';

export default function StatsCards({ dashboard }) {
  const stats = [
    {
      label: 'Total Spots',
      value: dashboard.total_spots,
      icon: MapPin,
      color: 'bg-blue-500',
      bg: 'bg-blue-50',
    },
    {
      label: 'Occupied',
      value: dashboard.total_occupied,
      icon: Car,
      color: 'bg-orange-500',
      bg: 'bg-orange-50',
      sub: `${dashboard.overall_occupancy_rate}%`,
    },
    {
      label: 'Available',
      value: dashboard.total_available,
      icon: Activity,
      color: 'bg-green-500',
      bg: 'bg-green-50',
    },
    {
      label: 'Events Today',
      value: dashboard.events_today,
      icon: Camera,
      color: 'bg-purple-500',
      bg: 'bg-purple-50',
      sub: `${dashboard.active_cameras} cameras`,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value.toLocaleString()}</p>
              {stat.sub && <p className="text-xs text-gray-400 mt-1">{stat.sub}</p>}
            </div>
            <div className={`${stat.bg} p-3 rounded-lg`}>
              <stat.icon className={`w-5 h-5 ${stat.color.replace('bg-', 'text-')}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

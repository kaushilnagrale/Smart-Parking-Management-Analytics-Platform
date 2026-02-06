import { ArrowDownLeft, ArrowUpRight, Clock } from 'lucide-react';

export default function RecentEvents({ events = [] }) {
  // Sample events if none from WebSocket
  const displayEvents = events.length > 0 ? events : [
    { event_type: 'entry', zone_code: 'A1', license_plate: 'AZ-1234', timestamp: new Date().toISOString() },
    { event_type: 'exit', zone_code: 'B1', license_plate: 'AZ-5678', timestamp: new Date(Date.now() - 120000).toISOString() },
    { event_type: 'entry', zone_code: 'C1', license_plate: 'CA-9012', timestamp: new Date(Date.now() - 300000).toISOString() },
    { event_type: 'entry', zone_code: 'E1', license_plate: 'TX-3456', timestamp: new Date(Date.now() - 600000).toISOString() },
    { event_type: 'exit', zone_code: 'A2', license_plate: 'AZ-7890', timestamp: new Date(Date.now() - 900000).toISOString() },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Recent Events</h3>

      <div className="space-y-3 max-h-64 overflow-y-auto">
        {displayEvents.slice(0, 10).map((event, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
          >
            <div className={`p-2 rounded-lg ${
              event.event_type === 'entry' ? 'bg-green-100' : 'bg-red-100'
            }`}>
              {event.event_type === 'entry' ? (
                <ArrowDownLeft className="w-4 h-4 text-green-600" />
              ) : (
                <ArrowUpRight className="w-4 h-4 text-red-600" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">
                {event.event_type === 'entry' ? 'Vehicle Entry' : 'Vehicle Exit'}
                <span className="text-gray-400 ml-2">→ Zone {event.zone_code}</span>
              </p>
              {event.license_plate && (
                <p className="text-xs text-gray-500 font-mono">{event.license_plate}</p>
              )}
            </div>

            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Clock className="w-3 h-3" />
              {event.timestamp
                ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : 'Now'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

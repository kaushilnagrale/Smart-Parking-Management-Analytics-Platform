import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Car } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-parking-800 to-parking-900">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-parking-100 rounded-full mb-4">
            <Car className="w-8 h-8 text-parking-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Smart Parking</h1>
          <p className="text-gray-500 mt-1">Management Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-parking-500 focus:border-transparent outline-none"
              placeholder="admin@smartparking.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-parking-500 focus:border-transparent outline-none"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-parking-600 hover:bg-parking-700 text-white font-medium py-2.5 rounded-lg transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-400 text-center">Demo Credentials</p>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-center">
            <button
              onClick={() => { setEmail('admin@smartparking.com'); setPassword('admin123'); }}
              className="py-1.5 bg-gray-100 rounded hover:bg-gray-200 transition"
            >
              Admin
            </button>
            <button
              onClick={() => { setEmail('operator@smartparking.com'); setPassword('operator123'); }}
              className="py-1.5 bg-gray-100 rounded hover:bg-gray-200 transition"
            >
              Operator
            </button>
            <button
              onClick={() => { setEmail('viewer@smartparking.com'); setPassword('viewer123'); }}
              className="py-1.5 bg-gray-100 rounded hover:bg-gray-200 transition"
            >
              Viewer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useRef } from 'react';
import { eventsAPI } from '../services/api';
import { Upload, Camera, Loader2 } from 'lucide-react';

export default function DetectionPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [annotatedImage, setAnnotatedImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setSelectedFile(file);
    setResult(null);
    setAnnotatedImage(null);
    setError(null);

    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target.result);
    reader.readAsDataURL(file);
  };

  const handleDetect = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    try {
      // Get annotated image
      const annotatedRes = await eventsAPI.detectAnnotated(selectedFile);
      setAnnotatedImage(annotatedRes.data.image);

      // Get structured detection data
      const detectRes = await eventsAPI.detect(selectedFile);
      setResult(detectRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed. Check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vehicle Detection</h1>
        <p className="text-gray-500 text-sm mt-1">
          Upload a parking lot image for vehicle detection and license plate recognition
        </p>
      </div>

      {/* Upload Area */}
      <div
        className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-parking-400 transition cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
        <p className="text-gray-600 font-medium">Click to upload a parking lot image</p>
        <p className="text-xs text-gray-400 mt-1">JPEG, PNG — Max 10MB</p>
      </div>

      {/* Preview & Results */}
      {preview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Original */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-700 mb-3">Original Image</h3>
            <img src={preview} alt="Original" className="w-full rounded-lg" />
          </div>

          {/* Annotated */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-700 mb-3">Detection Result</h3>
            {annotatedImage ? (
              <img src={annotatedImage} alt="Detected" className="w-full rounded-lg" />
            ) : (
              <div className="flex items-center justify-center h-48 bg-gray-50 rounded-lg text-gray-400">
                Click &quot;Run Detection&quot; to analyze
              </div>
            )}
          </div>
        </div>
      )}

      {/* Run Detection Button */}
      {selectedFile && (
        <button
          onClick={handleDetect}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-parking-600 hover:bg-parking-700 text-white font-medium px-6 py-2.5 rounded-lg transition disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
          {loading ? 'Processing...' : 'Run Detection'}
        </button>
      )}

      {error && (
        <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Detection Results Table */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">
            Detection Results — {result.vehicle_count} vehicles found
            <span className="text-sm font-normal text-gray-400 ml-2">
              ({result.processing_time_ms.toFixed(0)}ms)
            </span>
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">#</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Type</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Confidence</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">License Plate</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Bounding Box</th>
                </tr>
              </thead>
              <tbody>
                {result.vehicles.map((v, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3">{idx + 1}</td>
                    <td className="py-2 px-3">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        {v.class}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`font-mono ${v.confidence > 0.8 ? 'text-green-600' : 'text-orange-500'}`}>
                        {(v.confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-gray-700">
                      {v.license_plate || '—'}
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-400 font-mono">
                      [{v.bbox.join(', ')}]
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.license_plates.length > 0 && (
            <div className="mt-4 p-3 bg-green-50 rounded-lg">
              <p className="text-sm font-medium text-green-700">
                Recognized Plates: {result.license_plates.join(', ')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

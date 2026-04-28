import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { SentinelSidebar } from '../../components/shared/SentinelSidebar';
import { Search, Globe, Activity, Shield } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { cn, formatNumber } from '../../lib/utils';
import { apiGet } from '../../lib/api';
import { showToast } from '../../components/shared/GlobalToast';

const defaultCenter: [number, number] = [20, 0];

function MapController({ center }: { center: [number, number] }) {
  const map = useMap();
  React.useEffect(() => {
    map.invalidateSize();
    map.setView(center);
  }, [map, center]);
  return null;
}

export function ThreatMap() {
  const { user } = useAuth();
  const [violationMarkers, setViolationMarkers] = useState<any[]>([]);
  const [mapCenter, setMapCenter] = useState<[number, number]>(defaultCenter);
  const totalNodes = violationMarkers.length;
  const criticalCount = violationMarkers.filter((marker) => {
    const level = String(marker.severity ?? marker.sev ?? marker.risk ?? '').toLowerCase();
    return level.includes('critical') || level.includes('severe');
  }).length;
  const highCount = violationMarkers.filter((marker) => {
    const level = String(marker.severity ?? marker.sev ?? marker.risk ?? '').toLowerCase();
    return level.includes('high');
  }).length;
  const criticalPercent = totalNodes ? Math.round((criticalCount / totalNodes) * 100) : 0;
  const highPercent = totalNodes ? Math.round((highCount / totalNodes) * 100) : 0;

  useEffect(() => {
    const loadMarkers = async () => {
      try {
        const response = await apiGet<{ markers: any[] }>('/api/signals/threat-map/');
        if (response.markers?.length) {
          setViolationMarkers(response.markers);
        }
      } catch {
        // Keep fallback data
      }
    };
    loadMarkers();
  }, []);

  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setMapCenter([pos.coords.latitude, pos.coords.longitude]),
      () => undefined,
      { enableHighAccuracy: false, timeout: 8000 }
    );
  }, []);

  return (
    <div className="flex bg-brand-bg min-h-screen">
      <SentinelSidebar role="user" />
      <main className="flex-1 p-8 space-y-8 overflow-x-hidden relative flex flex-col">
        <div className="flex items-center justify-between relative z-10 flex-shrink-0">
          <div>
            <h1 className="mission-control-header !text-brand-accent mb-2">Authenticated: {user?.orgName || 'Your Organization'}</h1>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-danger animate-pulse" />
              <p className="text-xl font-bold text-white tracking-tight">Geospatial Intelligence Terminal</p>
            </div>
          </div>
          <div className="flex gap-4">
             <div className="flex items-center gap-2 px-4 py-2 glass-card border-white/5 bg-white/5">
               <div className="w-2 h-2 rounded-full bg-brand-danger animate-ping" />
               <span className="text-[10px] font-mono text-brand-danger font-bold tracking-widest uppercase">Live Pulse: {formatNumber(totalNodes)} nodes</span>
             </div>
             <button className="primary-button">
                <Search className="w-4 h-4" />
                Analyze Sector
             </button>
          </div>
        </div>

        <div className="flex-1 glass-card overflow-hidden relative min-h-[500px]">
          {/* Legend Panel */}
          <div className="absolute top-6 right-6 z-[1000] glass-card p-4 w-64 border-brand-accent/20">
            <h4 className="text-[10px] font-mono font-bold text-brand-accent uppercase tracking-widest mb-3">Live Risk Legend</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-brand-danger shadow-[0_0_8px_#EF4444]" />
                  <span className="text-[10px] text-white font-mono uppercase">Critical Takedown</span>
                </div>
                <span className="text-[10px] text-brand-muted">{criticalPercent}%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-brand-warn shadow-[0_0_8px_#F59E0B]" />
                  <span className="text-[10px] text-white font-mono uppercase">High Propagation</span>
                </div>
                <span className="text-[10px] text-brand-muted">{highPercent}%</span>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-white/5">
                <span className="text-[9px] text-brand-muted font-mono uppercase">Total Nodes</span>
                <span className="text-xs text-white font-bold font-mono">{formatNumber(totalNodes)}</span>
              </div>
            </div>
          </div>

          <MapContainer 
            center={mapCenter} 
            zoom={2} 
            scrollWheelZoom={true} 
            className="w-full h-full z-0"
            style={{ background: '#080C14' }}
            zoomControl={false}
          >
            <MapController center={mapCenter} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {violationMarkers.map((marker) => (
              <CircleMarker
                key={marker.id}
                center={marker.center as [number, number]}
                radius={8}
                pathOptions={{
                  fillColor: '#EF4444',
                  color: '#EF4444',
                  weight: 2,
                  opacity: 0.8,
                  fillOpacity: 0.4
                }}
              >
                <Popup className="sentinel-popup">
                  <div className="p-1">
                    <h5 className="font-bold text-gray-900">{marker.city}</h5>
                    <p className="text-xs text-red-600 font-mono mt-1">{marker.violations} violations detected</p>
                    <button className="mt-2 w-full text-[10px] bg-red-600 text-white font-bold py-1 rounded" onClick={() => showToast(`Analyzing ${marker.city}...`, 'info')}>ANALYZE CLUSTER</button>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
          {violationMarkers.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-xs text-brand-muted">
              No live threat markers yet.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-4 flex-shrink-0">
           <div className="glass-card p-6 border-brand-accent/20">
              <div className="flex items-center gap-4 mb-4">
                 <Activity className="w-5 h-5 text-brand-accent" />
                 <h4 className="text-white font-bold">Signal Intelligence</h4>
              </div>
              <p className="text-xs text-brand-muted leading-relaxed">
                 Sentinel’s global proxy network detects encrypted traffic patterns matching high-definition sports broadcast streams. 
                 Currently identifying a major synchronized leak cluster in the Eastern European sector.
              </p>
           </div>
           <div className="glass-card p-6 border-brand-danger/20">
              <div className="flex items-center gap-4 mb-4">
                 <Shield className="w-5 h-5 text-brand-danger" />
                 <h4 className="text-white font-bold">Automatic Interdiction</h4>
              </div>
              <p className="text-xs text-brand-muted leading-relaxed">
                 Active countermeasures deployed to 12 verified stream rippers. Redirecting traffic to legal broadcaster landing pages 
                 via simulated packet injection and ISP-level reporting.
              </p>
           </div>
        </div>
      </main>
    </div>
  );
}

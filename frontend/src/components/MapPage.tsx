import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import "./MapPage.css";

interface ParkingSign {
  id: string;
  latitude: number;
  longitude: number;
  description: string;
  sign_text: string;
  image_url: string | null;
  created_at: string;
}

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN as string;

// Default center: San Francisco
const DEFAULT_CENTER: [number, number] = [-122.4194, 37.7749];
const DEFAULT_ZOOM = 12;

export default function MapPage() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || !MAPBOX_TOKEN) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      accessToken: MAPBOX_TOKEN,
      style: "mapbox://styles/mapbox/streets-v12",
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    mapRef.current = map;

    fetch("/api/parking-signs")
      .then((res) => res.json())
      .then((signs: ParkingSign[]) => {
        if (signs.length === 0) return;

        const bounds = new mapboxgl.LngLatBounds();

        for (const sign of signs) {
          const lngLat: [number, number] = [sign.longitude, sign.latitude];
          bounds.extend(lngLat);

          const popupHtml = `
            <div class="sign-popup">
              ${sign.image_url ? `<img src="${sign.image_url}" alt="Parking sign" />` : ""}
              <p class="sign-text">${escapeHtml(sign.sign_text)}</p>
              <p class="sign-description">${escapeHtml(sign.description)}</p>
            </div>
          `;

          new mapboxgl.Marker()
            .setLngLat(lngLat)
            .setPopup(new mapboxgl.Popup({ maxWidth: "260px" }).setHTML(popupHtml))
            .addTo(map);
        }

        map.fitBounds(bounds, { padding: 60, maxZoom: 15 });
      })
      .catch((err) => console.error("Failed to fetch parking signs:", err));

    return () => {
      map.remove();
    };
  }, []);

  if (!MAPBOX_TOKEN) {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <h2>Mapbox token not configured</h2>
        <p>
          Set <code>VITE_MAPBOX_ACCESS_TOKEN</code> in{" "}
          <code>frontend/.env</code> and restart the dev server.
        </p>
        <Link to="/">Back to chat</Link>
      </div>
    );
  }

  return (
    <>
      <div ref={mapContainer} className="map-container" />
      <Link to="/" className="map-back-button">
        ← Chat
      </Link>
    </>
  );
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

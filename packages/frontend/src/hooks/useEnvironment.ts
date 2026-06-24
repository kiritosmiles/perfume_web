import { useState, useEffect } from "react";

export interface EnvironmentData {
  season: string | null;
  time_of_day: string | null;
  weather_code: number | null;
  temperature: number | null;
  weather_label: string | null;
  weather_emoji: string | null;
}

/** WMO weather codes → display label/emoji */
const WEATHER_MAP: Record<number, { label: string; emoji: string }> = {
  0: { label: "晴天", emoji: "☀️" },
  1: { label: "少云", emoji: "🌤️" },
  2: { label: "多云", emoji: "⛅" },
  3: { label: "阴天", emoji: "☁️" },
  45: { label: "雾", emoji: "🌫️" },
  48: { label: "霜雾", emoji: "🌫️" },
  51: { label: "小雨", emoji: "🌧" },
  53: { label: "中雨", emoji: "🌧" },
  55: { label: "大雨", emoji: "🌧" },
  61: { label: "小雨", emoji: "🌧" },
  63: { label: "中雨", emoji: "🌧" },
  65: { label: "大雨", emoji: "🌧" },
  71: { label: "小雪", emoji: "🌨️" },
  73: { label: "中雪", emoji: "🌨️" },
  75: { label: "大雪", emoji: "🌨️" },
  77: { label: "雪粒", emoji: "🌨️" },
  80: { label: "阵雨", emoji: "🌦️" },
  81: { label: "中阵雨", emoji: "🌦️" },
  82: { label: "大阵雨", emoji: "🌦️" },
  85: { label: "小雪阵", emoji: "🌨️" },
  86: { label: "大雪阵", emoji: "🌨️" },
  95: { label: "雷暴", emoji: "⛈️" },
  96: { label: "冰雹雷暴", emoji: "⛈️" },
  99: { label: "强冰雹", emoji: "⛈️" },
};

function getSeason(): string {
  const month = new Date().getMonth(); // 0-11
  if (month >= 2 && month <= 4) return "spring";
  if (month >= 5 && month <= 7) return "summer";
  if (month >= 8 && month <= 10) return "autumn";
  return "winter";
}

function getTimeOfDay(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour <= 11) return "morning";
  if (hour >= 12 && hour <= 17) return "afternoon";
  if (hour >= 18 && hour <= 21) return "evening";
  return "night";
}

function getWeatherLabel(code: number | null): { label: string | null; emoji: string | null } {
  if (code === null) return { label: null, emoji: null };
  const entry = WEATHER_MAP[code];
  if (entry) return entry;
  return { label: `天气码${code}`, emoji: "🌤" };
}

const SEASON_LABELS: Record<string, string> = {
  spring: "🌸 春", summer: "☀️ 夏", autumn: "🍂 秋", winter: "❄️ 冬",
};

const TOD_LABELS: Record<string, string> = {
  morning: "早晨", afternoon: "下午", evening: "傍晚", night: "深夜",
};

export function formatEnvironmentLabel(env: EnvironmentData): string {
  const parts: string[] = [];
  if (env.season) parts.push(SEASON_LABELS[env.season] || env.season);
  if (env.time_of_day) parts.push(TOD_LABELS[env.time_of_day] || env.time_of_day);
  if (env.weather_emoji) {
    const wLabel = env.weather_label || "";
    const tempStr = env.temperature !== null ? ` ${Math.round(env.temperature)}°C` : "";
    parts.push(`${env.weather_emoji} ${wLabel}${tempStr}`);
  } else if (env.temperature !== null) {
    parts.push(`${Math.round(env.temperature)}°C`);
  }
  return parts.join(" · ");
}

/**
 * Auto-detect environment (season, time of day, weather via Open-Meteo).
 * Weather is fetched asynchronously; season/time are instant.
 * If geolocation is denied or times out, weather is skipped gracefully.
 */
export function useEnvironment(): {
  env: EnvironmentData;
  enabled: boolean;
  setEnabled: (v: boolean) => void;
} {
  const [weatherCode, setWeatherCode] = useState<number | null>(null);
  const [temperature, setTemperature] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(true);

  // Weather fetch (async, gentle fallback)
  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    const timeout = setTimeout(() => {
      // Geolocation timeout — skip weather
    }, 5000);

    const fetchWeather = async (lat: number, lon: number) => {
      try {
        const res = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code`,
        );
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (data?.current) {
          setWeatherCode(data.current.weather_code ?? null);
          setTemperature(data.current.temperature_2m ?? null);
        }
      } catch {
        // Silently skip weather on network errors
      }
    };

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          if (!cancelled) {
            clearTimeout(timeout);
            fetchWeather(pos.coords.latitude, pos.coords.longitude);
          }
        },
        () => {
          // Permission denied or error — skip weather gracefully
        },
        { timeout: 5000, maximumAge: 30 * 60 * 1000 }, // Cache 30 min
      );
    }

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [enabled]);

  const { label, emoji } = getWeatherLabel(weatherCode);

  return {
    env: {
      season: getSeason(),
      time_of_day: getTimeOfDay(),
      weather_code: weatherCode,
      temperature,
      weather_label: label,
      weather_emoji: emoji,
    },
    enabled,
    setEnabled,
  };
}

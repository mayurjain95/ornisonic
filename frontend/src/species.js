const imageCache = new Map();

async function fetchThumbnail(title) {
  const res = await fetch(
    `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.thumbnail?.source || null;
}

/**
 * Looks up a species photo on Wikipedia, trying the common name first and
 * falling back to the scientific name. Returns null if neither resolves.
 */
export async function getSpeciesImage(commonName, scientificName) {
  const cacheKey = commonName || scientificName;
  if (!cacheKey) return null;
  if (imageCache.has(cacheKey)) return imageCache.get(cacheKey);

  let url = null;
  try {
    if (commonName) url = await fetchThumbnail(commonName);
    if (!url && scientificName) url = await fetchThumbnail(scientificName);
  } catch {
    url = null;
  }

  imageCache.set(cacheKey, url);
  return url;
}

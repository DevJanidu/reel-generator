export async function api(path: string, method = 'GET', body?: unknown) {
  const res = await fetch('/api' + path, {
    method,
    headers: {'Content-Type': 'application/json', 'X-Odd-Controller': sessionStorage.getItem('odd-frame-controller') || ''},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

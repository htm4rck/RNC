export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const basePath = window.location.pathname.startsWith('/rcn/ui') ? '/rcn/api' : '/api';

  return `${basePath}${normalizedPath}`;
}

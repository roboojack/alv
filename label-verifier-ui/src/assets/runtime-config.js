(function applyRuntimeApiBase() {
	if (typeof window === 'undefined' || window.__ALV_API__) {
		return;
	}

	const { hostname } = window.location;
	const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';

	// Firebase Hosting rewrites /api/** to Cloud Run, so production can stay relative.
	window.__ALV_API__ = isLocal ? 'http://localhost:8000/api' : '/api';
})();

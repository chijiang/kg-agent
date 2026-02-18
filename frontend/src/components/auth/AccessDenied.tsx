// frontend/src/components/auth/AccessDenied.tsx
export function AccessDeniedPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Access Denied</h1>
        <p className="text-gray-600 mb-8">You don't have permission to access this page.</p>
        <a href="/" className="text-blue-600 hover:text-blue-800">
          Return to Home
        </a>
      </div>
    </div>
  )
}

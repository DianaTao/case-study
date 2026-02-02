'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect directly to chat page
    router.push('/chat');
  }, [router]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-partselect-primary mx-auto"></div>
        <p className="mt-4 text-partselect-text-secondary">Loading...</p>
      </div>
    </main>
  );
}

'use client';

import { formatDistanceToNow } from 'date-fns';
import { useEffect, useState } from 'react';

export function RelativeTime({ iso }: { iso: string }) {
  const [label, setLabel] = useState('');

  useEffect(() => {
    const update = () =>
      setLabel(formatDistanceToNow(new Date(iso), { addSuffix: true }));
    update();
    const id = setInterval(update, 30_000);
    return () => clearInterval(id);
  }, [iso]);

  return (
    <time dateTime={iso} title={iso} className="text-xs text-muted-foreground">
      {label}
    </time>
  );
}

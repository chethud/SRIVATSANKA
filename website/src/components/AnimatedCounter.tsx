import { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';

export function AnimatedCounter({
  value,
  format = (n) => String(Math.round(n)),
}: {
  value: number;
  format?: (n: number) => string;
}) {
  const spring = useSpring(0, { stiffness: 90, damping: 18 });
  const [display, setDisplay] = useState(format(0));

  useEffect(() => {
    spring.set(value);
    const unsub = spring.on('change', (v) => setDisplay(format(v)));
    return unsub;
  }, [value, spring, format]);

  return <motion.span>{display}</motion.span>;
}

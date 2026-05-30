import { writable } from 'svelte/store';

// Holds the most recent scroll delta (difference between frames)
export const scrollDelta = writable(0);

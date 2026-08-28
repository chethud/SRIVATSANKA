export const MAX_PHOTOS_PER_EVENT = 5;

export type PhotoEventDef = {
  eventType: string;
  coverUrl: string;
  blurb: string;
};

export const PHOTO_EVENTS: PhotoEventDef[] = [
  {
    eventType: 'Wedding',
    coverUrl: 'https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240103203446-scaled.jpg',
    blurb: 'Wedding photos — up to 5 images',
  },
  {
    eventType: 'Birthday',
    coverUrl: 'https://srivatsanka.com/wp-content/uploads/2026/03/IMG20240827170330-Copy-scaled.jpg',
    blurb: 'Birthday photos — up to 5 images',
  },
  {
    eventType: 'Corporate events',
    coverUrl: 'https://srivatsanka.com/wp-content/uploads/2026/03/IMG20250120130855-scaled.jpg',
    blurb: 'Corporate event photos — up to 5 images',
  },
];

export const SDG_COLORS: Record<number, string> = {
  1: '#E5243B',
  2: '#DDA63A',
  3: '#4C9F38',
  4: '#C5192D',
  5: '#FF3A21',
  6: '#26BDE2',
  7: '#FCC30B',
  8: '#A21942',
  9: '#FD6925',
  10: '#DD1367',
  11: '#FD9D24',
  12: '#BF8B2E',
  13: '#3F7E44',
  14: '#0A97D9',
  15: '#56C02B',
  16: '#00689D',
  17: '#19486A',
}

export function getSDGColor(sdg: number): string {
  return SDG_COLORS[sdg] ?? '#6b7280'
}

/** Short goal names, as used in ledger rows and table headers. */
export const SDG_NAMES: Record<number, string> = {
  1: 'No Poverty',
  2: 'Zero Hunger',
  3: 'Good Health',
  4: 'Quality Education',
  5: 'Gender Equality',
  6: 'Clean Water',
  7: 'Clean Energy',
  8: 'Decent Work',
  9: 'Innovation',
  10: 'Reduced Inequalities',
  11: 'Sustainable Cities',
  12: 'Responsible Consumption',
  13: 'Climate Action',
  14: 'Life Below Water',
  15: 'Life on Land',
  16: 'Peace & Justice',
  17: 'Partnerships',
}

export function getSDGName(sdg: number): string {
  return SDG_NAMES[sdg] ?? `Goal ${sdg}`
}

/** Full official goal names, for headers (not the short table labels). */
export const SDG_OFFICIAL: Record<number, string> = {
  1: 'End poverty in all its forms everywhere',
  2: 'End hunger, achieve food security and improved nutrition',
  3: 'Ensure healthy lives and well-being for all at all ages',
  4: 'Ensure inclusive and equitable quality education',
  5: 'Achieve gender equality and empower all women and girls',
  6: 'Ensure availability and sustainable management of water',
  7: 'Ensure access to affordable, reliable, sustainable energy',
  8: 'Promote sustained, inclusive economic growth and decent work',
  9: 'Build resilient infrastructure and foster innovation',
  10: 'Reduce inequality within and among countries',
  11: 'Make cities inclusive, safe, resilient and sustainable',
  12: 'Ensure sustainable consumption and production patterns',
  13: 'Take urgent action to combat climate change',
  14: 'Conserve and sustainably use the oceans and marine resources',
  15: 'Protect and restore terrestrial ecosystems',
  16: 'Promote peaceful, inclusive societies and strong institutions',
  17: 'Strengthen the means of implementation and global partnership',
}

export function getSDGOfficial(sdg: number): string {
  return SDG_OFFICIAL[sdg] ?? ''
}

// Full official Goal titles — for published/statement copy (the design uses
// these, not the SDG_NAMES table-header abbreviations).
export const SDG_TITLE: Record<number, string> = {
  1: 'No Poverty', 2: 'Zero Hunger', 3: 'Good Health and Well-being', 4: 'Quality Education',
  5: 'Gender Equality', 6: 'Clean Water and Sanitation', 7: 'Affordable and Clean Energy',
  8: 'Decent Work and Economic Growth', 9: 'Industry, Innovation and Infrastructure',
  10: 'Reduced Inequalities', 11: 'Sustainable Cities and Communities',
  12: 'Responsible Consumption and Production', 13: 'Climate Action', 14: 'Life Below Water',
  15: 'Life on Land', 16: 'Peace, Justice and Strong Institutions', 17: 'Partnerships for the Goals',
}

export function getSDGTitle(sdg: number): string {
  return SDG_TITLE[sdg] ?? `Goal ${sdg}`
}

export const SDG_COUNT = 17

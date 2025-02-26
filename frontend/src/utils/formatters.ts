export const formatBalance = (value: number | string | undefined): string => {
  if (value === undefined || value === '') return '-';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '-';
  return numValue.toFixed(2);
};

export const formatPrice = (value: number | string | undefined): string => {
  if (value === undefined || value === '') return '-';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '-';
  return numValue.toFixed(2);
};

export const formatQuantity = (value: number | string | undefined): string => {
  if (value === undefined || value === '') return '-';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '-';
  return numValue.toFixed(4);
};

export const formatPnL = (value: number | string | undefined): string => {
  if (value === undefined || value === '') return '-';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return '-';
  const formatted = numValue.toFixed(2);
  return numValue >= 0 ? `+${formatted}` : formatted;
}; 
export const formatBalance = (value: number | undefined): string => {
  if (value === undefined) return '-';
  return value.toFixed(2);
};

export const formatPrice = (value: number | undefined): string => {
  if (value === undefined) return '-';
  return value.toFixed(2);
};

export const formatQuantity = (value: number | undefined): string => {
  if (value === undefined) return '-';
  return value.toFixed(4);
};

export const formatPnL = (value: number | undefined): string => {
  if (value === undefined) return '-';
  const formatted = value.toFixed(2);
  return value >= 0 ? `+${formatted}` : formatted;
}; 
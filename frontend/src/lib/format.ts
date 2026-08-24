import { ApiError } from "../client/api";

export const money = (value: string | number, currency: string) => {
  const amount = new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
  const symbol = currency === "PEN" ? "S/." : currency === "USD" ? "$" : currency;
  return `${symbol} ${amount}`;
};

export const errorText = (error: unknown) =>
  error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : "No fue posible completar la operacion.";

export const today = () => new Date().toISOString().slice(0, 10);

export const dateValue = (offset: number) => {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
};

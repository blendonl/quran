import { useColorScheme } from "nativewind";
import { TextStyle, ViewStyle } from "react-native";

interface ColorScale {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  950?: string;
}

interface SurfaceColors {
  bg: string;
  card: string;
  cardAlt: string;
  separator: string;
  elevated: string;
}

interface InkColors {
  base: string;
  secondary: string;
  muted: string;
}

interface StatusColors {
  CORRECT: string;
  INCORRECT: string;
  NOT_SURE: string;
}

interface TajweedColors {
  excellent: string;
  good: string;
  needs_work: string;
  missed: string;
}

interface ConnectionColors {
  connected: string;
  connecting: string;
  disconnected: string;
}

export interface ThemeColors {
  primary: ColorScale;
  gold: ColorScale;
  surface: SurfaceColors;
  ink: InkColors;
  status: StatusColors;
  tajweed: TajweedColors;
  connection: ConnectionColors;
}

const LIGHT: ThemeColors = {
  primary: {
    50: "#EEF6F0",
    100: "#D0E8D6",
    200: "#A8D4B4",
    300: "#74BC8C",
    400: "#3FA066",
    500: "#1A6B42",
    600: "#165C38",
    700: "#12472C",
    800: "#0E3822",
    900: "#0A2918",
    950: "#061A0F",
  },
  gold: {
    50: "#FEF9EE",
    100: "#FBF0D1",
    200: "#F6E0A0",
    300: "#F0CC68",
    400: "#E9B840",
    500: "#C4920E",
    600: "#A47A0B",
    700: "#846208",
    800: "#644A06",
    900: "#443204",
  },
  surface: {
    bg: "#F6F5F2",
    card: "#FFFFFF",
    cardAlt: "#F9F8F6",
    separator: "#E5E3DE",
    elevated: "#EDEBE7",
  },
  ink: {
    base: "#1C2127",
    secondary: "#5A6270",
    muted: "#7D8490",
  },
  status: {
    CORRECT: "#2A7D4F",
    INCORRECT: "#C43D2F",
    NOT_SURE: "#C4920E",
  },
  tajweed: {
    excellent: "#1A6B42",
    good: "#2A7D4F",
    needs_work: "#C4920E",
    missed: "#C43D2F",
  },
  connection: {
    connected: "#2A7D4F",
    connecting: "#E9B840",
    disconnected: "#C43D2F",
  },
};

const DARK: ThemeColors = {
  primary: {
    50: "#0D1F14",
    100: "#132B1C",
    200: "#1A3D28",
    300: "#236B40",
    400: "#2E8B57",
    500: "#3DA870",
    600: "#52C08A",
    700: "#7CD4A6",
    800: "#A8E4C4",
    900: "#D4F2E2",
    950: "#E8F5EC",
  },
  gold: {
    50: "#1A1508",
    100: "#2A220D",
    200: "#3D3214",
    300: "#6B571F",
    400: "#9A7F2E",
    500: "#C4A03A",
    600: "#D4B454",
    700: "#E0C878",
    800: "#ECD9A0",
    900: "#F4EAC8",
  },
  surface: {
    bg: "#131517",
    card: "#1C1E22",
    cardAlt: "#222428",
    separator: "#2C2E33",
    elevated: "#191B1F",
  },
  ink: {
    base: "#E4E6EA",
    secondary: "#9EA3AB",
    muted: "#636870",
  },
  status: {
    CORRECT: "#4CAF72",
    INCORRECT: "#E06050",
    NOT_SURE: "#D4B454",
  },
  tajweed: {
    excellent: "#3DA870",
    good: "#4CAF72",
    needs_work: "#D4B454",
    missed: "#E06050",
  },
  connection: {
    connected: "#4CAF72",
    connecting: "#9A7F2E",
    disconnected: "#E06050",
  },
};

export function useThemeColors(): ThemeColors {
  const { colorScheme } = useColorScheme();
  return colorScheme === "dark" ? DARK : LIGHT;
}

export const TYPOGRAPHY = {
  ARABIC_LINE_HEIGHT_RATIO: 1.8,
  TRANSLATION_SCALE: 0.6,
  MIN_TRANSLATION_SIZE: 14,
} as const;

export const RTL_TEXT: TextStyle = { writingDirection: "rtl" };
export const RTL_VIEW: ViewStyle = { direction: "rtl" };

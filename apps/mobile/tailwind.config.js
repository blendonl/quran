/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        ivory: "#F6F5F2",
        cream: "#F9F8F6",
        "surface-card": "#FFFFFF",
        "surface-sep": "#E5E3DE",
        "surface-elevated": "#EDEBE7",

        "d-bg": "#131517",
        "d-card": "#1C1E22",
        "d-card-alt": "#222428",
        "d-sep": "#2C2E33",
        "d-elevated": "#191B1F",

        ink: { DEFAULT: "#1C2127", secondary: "#5A6270", muted: "#7D8490" },
        "d-ink": { DEFAULT: "#E4E6EA", secondary: "#9EA3AB", muted: "#636870" },

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
      },
      fontFamily: {
        arabic: ["Amiri"],
        "arabic-bold": ["Amiri-Bold"],
      },
    },
  },
  plugins: [],
};

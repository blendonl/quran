/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0f9f4",
          100: "#d9f0e3",
          200: "#b5e1c9",
          300: "#84cba8",
          400: "#51b083",
          500: "#2f9568",
          600: "#1f7853",
          700: "#196044",
          800: "#164d37",
          900: "#133f2f",
          950: "#0a231a",
        },
        gold: {
          50: "#fdfaef",
          100: "#faf0d0",
          200: "#f4e09d",
          300: "#edca64",
          400: "#e7b53e",
          500: "#de9a22",
          600: "#c4781a",
          700: "#a35818",
          800: "#86461b",
          900: "#6e3b19",
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

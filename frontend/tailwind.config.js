/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: "#eef5ff",
                    100: "#d9e8ff",
                    200: "#bcd8ff",
                    300: "#8ec1ff",
                    400: "#59a0ff",
                    500: "#3378ff",
                    600: "#1b57f5",
                    700: "#1443e1",
                    800: "#1736b6",
                    900: "#19338f",
                    950: "#142157",
                },
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
            },
        },
    },
    plugins: [],
};
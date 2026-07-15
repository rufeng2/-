import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, ".", "");
    var apiTarget = env.VITE_API_TARGET || "http://localhost:8000";
    return {
        plugins: [vue()],
        resolve: {
            alias: {
                "@": "/src",
            },
        },
        server: {
            port: 5173,
            proxy: {
                "/api": {
                    target: apiTarget,
                    changeOrigin: true,
                },
            },
        },
    };
});

import { useState, useCallback } from "react";
import Dashboard from "./components/Dashboard";

const MERCHANTS = [
    { id: 1, name: "Acme Freelancers" },
    { id: 2, name: "DesignStudio India" },
    { id: 3, name: "CodeCraft Agency" },
];

function Toast({ message, type, onClose }) {
    return (
        <div
            className={`toast flex items-center gap-3 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur-md ${type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : type === "error"
                        ? "bg-red-500/10 border-red-500/20 text-red-400"
                        : "bg-blue-500/10 border-blue-500/20 text-blue-400"
                }`}
        >
            {type === "success" && (
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
            )}
            {type === "error" && (
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                </svg>
            )}
            {type === "info" && (
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
                </svg>
            )}
            <span className="text-sm font-medium">{message}</span>
            <button onClick={onClose} className="ml-auto text-gray-500 hover:text-gray-300 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    );
}

export default function App() {
    const [merchantId, setMerchantId] = useState(1);
    const [toasts, setToasts] = useState([]);
    const merchant = MERCHANTS.find((m) => m.id === merchantId);

    const addToast = useCallback((message, type = "info") => {
        const id = Date.now();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 4000);
    }, []);

    const removeToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return (
        <div className="min-h-screen">
            <div className="fixed top-20 right-6 z-50 flex flex-col gap-2 max-w-sm">
                {toasts.map((toast) => (
                    <Toast
                        key={toast.id}
                        message={toast.message}
                        type={toast.type}
                        onClose={() => removeToast(toast.id)}
                    />
                ))}
            </div>

            <header className="border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-40">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center shadow-lg shadow-brand-600/20">
                            <svg
                                className="w-4.5 h-4.5 text-white"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2.5}
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"
                                />
                            </svg>
                        </div>
                        <div>
                            <span className="text-lg font-extrabold text-white tracking-tight">
                                Playto
                            </span>
                            <span className="text-[11px] text-gray-500 font-semibold ml-2 hidden sm:inline tracking-wide uppercase">
                                Payout Engine
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center gap-5">
                        <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1 rounded-full">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-[11px] text-emerald-400 font-semibold">
                                Live
                            </span>
                        </div>
                        <div className="relative">
                            <select
                                value={merchantId}
                                onChange={(e) => setMerchantId(Number(e.target.value))}
                                className="bg-gray-800/80 border border-gray-700/60 rounded-xl pl-3 pr-9 py-2 text-sm
                           text-white font-medium appearance-none cursor-pointer
                           hover:border-gray-600 transition-all duration-200
                           focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                            >
                                {MERCHANTS.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {m.name}
                                    </option>
                                ))}
                            </select>
                            <svg
                                className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2}
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="m19.5 8.25-7.5 7.5-7.5-7.5"
                                />
                            </svg>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-10">
                <div className="mb-10 slide-up">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center">
                            <span className="text-brand-400 font-extrabold text-lg">
                                {merchant.name.charAt(0)}
                            </span>
                        </div>
                        <div>
                            <h1 className="text-2xl font-extrabold text-white tracking-tight">
                                {merchant.name}
                            </h1>
                            <p className="text-sm text-gray-500">
                                Manage payouts, view balances, and track transactions
                            </p>
                        </div>
                    </div>
                </div>
                <Dashboard key={merchantId} merchantId={merchantId} addToast={addToast} />
            </main>

            <footer className="border-t border-gray-800/40 mt-20">
                <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
                    <span className="text-xs text-gray-600">
                        Playto Payout Engine — Built for correctness
                    </span>
                    <span className="text-xs text-gray-700">
                        All amounts in INR paise
                    </span>
                </div>
            </footer>
        </div>
    );
}
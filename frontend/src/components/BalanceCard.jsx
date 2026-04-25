import { useCallback } from "react";
import { getBalance } from "../api/client";
import usePolling from "../hooks/usePolling";

function formatPaise(paise) {
    const rupees = Math.abs(paise) / 100;
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
    }).format(rupees);
}

function SkeletonCard() {
    return (
        <div className="card shimmer">
            <div className="flex items-center justify-between mb-4">
                <div className="h-3 w-28 bg-gray-800 rounded animate-pulse" />
                <div className="h-9 w-9 bg-gray-800 rounded-xl animate-pulse" />
            </div>
            <div className="h-9 w-44 bg-gray-800 rounded-lg animate-pulse mb-2" />
            <div className="h-3 w-32 bg-gray-800/60 rounded animate-pulse" />
        </div>
    );
}

export default function BalanceCard({ merchantId }) {
    const fetchBalance = useCallback(
        () => getBalance(merchantId),
        [merchantId]
    );
    const { data, loading, error } = usePolling(fetchBalance, 3000);

    if (error) {
        return (
            <div className="card border-red-500/20">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-red-500/10 flex items-center justify-center">
                        <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                        </svg>
                    </div>
                    <p className="text-sm text-red-400 font-medium">Failed to load balance</p>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <SkeletonCard />
                <SkeletonCard />
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 slide-up">
            <div className="card group hover:border-emerald-500/30 transition-all duration-300">
                <div className="flex items-center justify-between mb-4">
                    <span className="card-header">Available Balance</span>
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors duration-300">
                        <svg
                            className="w-4 h-4 text-emerald-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={2}
                            stroke="currentColor"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"
                            />
                        </svg>
                    </div>
                </div>
                <span className="card-value text-emerald-400">
                    {formatPaise(data.available_balance)}
                </span>
                <p className="text-xs text-gray-600 mt-2.5">
                    Withdrawable right now
                </p>
            </div>

            <div className="card group hover:border-yellow-500/30 transition-all duration-300">
                <div className="flex items-center justify-between mb-4">
                    <span className="card-header">Held in Payouts</span>
                    <div className="w-9 h-9 rounded-xl bg-yellow-500/10 flex items-center justify-center group-hover:bg-yellow-500/20 transition-colors duration-300">
                        <svg
                            className="w-4 h-4 text-yellow-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={2}
                            stroke="currentColor"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                            />
                        </svg>
                    </div>
                </div>
                <span className="card-value text-yellow-400">
                    {formatPaise(data.held_balance)}
                </span>
                <p className="text-xs text-gray-600 mt-2.5">
                    Pending &amp; processing payouts
                </p>
            </div>
        </div>
    );
}
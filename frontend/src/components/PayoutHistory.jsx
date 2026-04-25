import { useCallback } from "react";
import { getPayouts } from "../api/client";
import usePolling from "../hooks/usePolling";

function formatPaise(paise) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
    }).format(paise / 100);
}

function formatTime(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;

    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function StatusBadge({ status }) {
    const config = {
        pending: { cls: "badge badge-pending", label: "Pending", pulse: false },
        processing: { cls: "badge badge-processing", label: "Processing", pulse: true },
        completed: { cls: "badge badge-completed", label: "Completed", pulse: false },
        failed: { cls: "badge badge-failed", label: "Failed", pulse: false },
    };

    const c = config[status] || config.pending;

    return (
        <span className={c.cls}>
            {c.pulse && <span className="pulse-dot pulse-dot-processing mr-1.5" />}
            {c.label}
        </span>
    );
}

function PayoutRow({ payout }) {
    return (
        <tr className="group hover:bg-gray-800/30 transition-colors duration-150">
            <td className="table-cell">
                <span className="text-xs font-mono text-gray-500 group-hover:text-gray-400 transition-colors">
                    #{payout.id}
                </span>
            </td>
            <td className="table-cell font-semibold text-white">
                {formatPaise(payout.amount_paise)}
            </td>
            <td className="table-cell">
                <StatusBadge status={payout.status} />
            </td>
            <td className="table-cell text-gray-500">
                {payout.attempt_count > 0 && (
                    <span className="text-xs font-medium">
                        {payout.attempt_count} attempt{payout.attempt_count !== 1 ? "s" : ""}
                    </span>
                )}
            </td>
            <td className="table-cell text-right text-gray-500 text-xs font-medium">
                {formatTime(payout.created_at)}
            </td>
        </tr>
    );
}

function EmptyState() {
    return (
        <div className="text-center py-12">
            <div className="w-14 h-14 rounded-2xl bg-gray-800/80 flex items-center justify-center mx-auto mb-4">
                <svg
                    className="w-6 h-6 text-gray-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                    />
                </svg>
            </div>
            <p className="text-sm text-gray-400 font-medium">No payouts yet</p>
            <p className="text-xs text-gray-600 mt-1">
                Create your first payout using the form
            </p>
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div className="space-y-4 py-2">
            {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 px-4">
                    <div className="h-4 w-8 bg-gray-800 rounded animate-pulse" />
                    <div className="h-4 w-24 bg-gray-800 rounded animate-pulse" />
                    <div className="h-6 w-20 bg-gray-800 rounded-full animate-pulse" />
                    <div className="flex-1" />
                    <div className="h-4 w-16 bg-gray-800 rounded animate-pulse" />
                </div>
            ))}
        </div>
    );
}

export default function PayoutHistory({ merchantId, refreshKey }) {
    const fetchPayouts = useCallback(
        () => getPayouts(merchantId),
        [merchantId]
    );
    const { data, loading, error } = usePolling(fetchPayouts, 3000);

    if (error) {
        return <p className="text-sm text-red-400 py-4">Failed to load payouts</p>;
    }

    if (loading) return <LoadingSkeleton />;
    if (!data || data.length === 0) return <EmptyState />;

    const sorted = [...data].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    const activeCount = sorted.filter(
        (p) => p.status === "pending" || p.status === "processing"
    ).length;

    return (
        <div className="fade-in">
            {activeCount > 0 && (
                <div className="flex items-center gap-2 mb-4 px-1 py-2 bg-blue-500/5 rounded-lg border border-blue-500/10">
                    <span className="pulse-dot pulse-dot-processing ml-2" />
                    <span className="text-xs text-blue-400 font-semibold">
                        {activeCount} payout{activeCount !== 1 ? "s" : ""} in progress
                    </span>
                </div>
            )}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-gray-800/60">
                            <th className="table-header py-3 px-4">ID</th>
                            <th className="table-header py-3 px-4">Amount</th>
                            <th className="table-header py-3 px-4">Status</th>
                            <th className="table-header py-3 px-4">Retries</th>
                            <th className="table-header py-3 px-4 text-right">Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map((payout) => (
                            <PayoutRow key={payout.id} payout={payout} />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
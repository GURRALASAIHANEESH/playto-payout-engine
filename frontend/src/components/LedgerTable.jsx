import { useCallback } from "react";
import { getLedger } from "../api/client";
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
    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function EntryRow({ entry }) {
    const isCredit = entry.entry_type === "CREDIT";

    return (
        <tr className="hover:bg-gray-800/50 transition-colors duration-150">
            <td className="table-cell">
                <div className="flex items-center gap-2.5">
                    <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center ${isCredit ? "bg-emerald-500/10" : "bg-red-500/10"
                            }`}
                    >
                        {isCredit ? (
                            <svg
                                className="w-3.5 h-3.5 text-emerald-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2.5}
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3"
                                />
                            </svg>
                        ) : (
                            <svg
                                className="w-3.5 h-3.5 text-red-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2.5}
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18"
                                />
                            </svg>
                        )}
                    </div>
                    <span
                        className={`text-xs font-semibold uppercase tracking-wide ${isCredit ? "text-emerald-400" : "text-red-400"
                            }`}
                    >
                        {entry.entry_type}
                    </span>
                </div>
            </td>
            <td className="table-cell font-medium text-white">
                <span className={isCredit ? "text-emerald-400" : "text-red-400"}>
                    {isCredit ? "+" : "−"} {formatPaise(entry.amount_paise)}
                </span>
            </td>
            <td className="table-cell text-gray-500 text-xs">
                {entry.payout ? (
                    <span className="inline-flex items-center gap-1 bg-gray-800 px-2 py-0.5 rounded-md font-mono">
                        Payout #{entry.payout}
                    </span>
                ) : (
                    <span className="text-gray-600">—</span>
                )}
            </td>
            <td className="table-cell text-right text-gray-500 text-xs">
                {formatTime(entry.created_at)}
            </td>
        </tr>
    );
}

function EmptyState() {
    return (
        <div className="text-center py-10">
            <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-3">
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
                        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                    />
                </svg>
            </div>
            <p className="text-sm text-gray-500">No ledger entries yet</p>
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div className="space-y-3 py-2">
            {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-4 px-4">
                    <div className="h-7 w-7 bg-gray-800 rounded-lg animate-pulse" />
                    <div className="h-4 w-16 bg-gray-800 rounded animate-pulse" />
                    <div className="h-4 w-24 bg-gray-800 rounded animate-pulse" />
                    <div className="flex-1" />
                    <div className="h-4 w-28 bg-gray-800 rounded animate-pulse" />
                </div>
            ))}
        </div>
    );
}

function LedgerSummary({ entries }) {
    const totalCredits = entries
        .filter((e) => e.entry_type === "CREDIT")
        .reduce((sum, e) => sum + e.amount_paise, 0);

    const totalDebits = entries
        .filter((e) => e.entry_type === "DEBIT")
        .reduce((sum, e) => sum + e.amount_paise, 0);

    return (
        <div className="flex items-center gap-4 mb-4 text-xs">
            <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-gray-500">Credits:</span>
                <span className="text-emerald-400 font-semibold">
                    {formatPaise(totalCredits)}
                </span>
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-gray-500">Debits:</span>
                <span className="text-red-400 font-semibold">
                    {formatPaise(totalDebits)}
                </span>
            </div>
            <div className="flex items-center gap-1.5 ml-auto">
                <span className="text-gray-500">Entries:</span>
                <span className="text-gray-300 font-semibold">{entries.length}</span>
            </div>
        </div>
    );
}

export default function LedgerTable({ merchantId, refreshKey }) {
    const fetchLedger = useCallback(
        () => getLedger(merchantId),
        [merchantId]
    );
    const { data, loading, error } = usePolling(fetchLedger, 5000);

    if (error) {
        return (
            <p className="text-sm text-red-400 py-4">Failed to load ledger</p>
        );
    }

    if (loading) return <LoadingSkeleton />;
    if (!data || data.length === 0) return <EmptyState />;

    const sorted = [...data].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    return (
        <div className="fade-in">
            <LedgerSummary entries={data} />
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-gray-800">
                            <th className="table-header py-2 px-4">Type</th>
                            <th className="table-header py-2 px-4">Amount</th>
                            <th className="table-header py-2 px-4">Reference</th>
                            <th className="table-header py-2 px-4 text-right">Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map((entry) => (
                            <EntryRow key={entry.id} entry={entry} />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
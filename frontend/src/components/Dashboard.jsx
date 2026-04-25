import { useState } from "react";
import BalanceCard from "./BalanceCard";
import PayoutForm from "./PayoutForm";
import PayoutHistory from "./PayoutHistory";
import LedgerTable from "./LedgerTable";

export default function Dashboard({ merchantId, addToast }) {
    const [refreshKey, setRefreshKey] = useState(0);

    const onPayoutCreated = () => {
        setRefreshKey((k) => k + 1);
    };

    return (
        <div className="space-y-6 slide-up">
            <BalanceCard key={`balance-${refreshKey}`} merchantId={merchantId} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                    <div className="card h-full flex flex-col">
                        <div className="flex items-center gap-2 mb-5">
                            <div className="w-7 h-7 rounded-lg bg-brand-600/10 flex items-center justify-center">
                                <svg className="w-3.5 h-3.5 text-brand-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                                </svg>
                            </div>
                            <h2 className="card-header mb-0">Request Payout</h2>
                        </div>
                        <PayoutForm
                            merchantId={merchantId}
                            onPayoutCreated={onPayoutCreated}
                            addToast={addToast}
                        />
                    </div>
                </div>
                <div className="lg:col-span-2 space-y-6">
                    <div className="card">
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
                                    <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
                                    </svg>
                                </div>
                                <h2 className="card-header mb-0">Payout History</h2>
                            </div>
                            <span className="text-[10px] text-gray-600 font-bold uppercase tracking-[0.15em]">
                                Auto-refreshing
                            </span>
                        </div>
                        <PayoutHistory
                            merchantId={merchantId}
                            refreshKey={refreshKey}
                        />
                    </div>
                    <div className="card">
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-lg bg-purple-500/10 flex items-center justify-center">
                                    <svg className="w-3.5 h-3.5 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                                    </svg>
                                </div>
                                <h2 className="card-header mb-0">Ledger</h2>
                            </div>
                            <span className="text-[10px] text-gray-600 font-bold uppercase tracking-[0.15em]">
                                All transactions
                            </span>
                        </div>
                        <LedgerTable
                            merchantId={merchantId}
                            refreshKey={refreshKey}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
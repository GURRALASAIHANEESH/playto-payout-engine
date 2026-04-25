import { useState, useRef } from "react";
import { createPayout } from "../api/client";

const BANK_ACCOUNTS = {
    1: [{ id: 1, label: "HDFC •••• 1234", holder: "Acme Freelancers" }],
    2: [{ id: 2, label: "ICICI •••• 5678", holder: "DesignStudio India" }],
    3: [{ id: 3, label: "SBI •••• 9012", holder: "CodeCraft Agency" }],
};

function generateIdempotencyKey() {
    return `pyt-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export default function PayoutForm({ merchantId, onPayoutCreated, addToast }) {
    const [amount, setAmount] = useState("");
    const [bankAccountId, setBankAccountId] = useState(
        BANK_ACCOUNTS[merchantId]?.[0]?.id || ""
    );
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const submittingRef = useRef(false);

    const accounts = BANK_ACCOUNTS[merchantId] || [];

    async function handleSubmit(e) {
        e.preventDefault();
        if (submittingRef.current) return;
        submittingRef.current = true;
        setSubmitting(true);
        setError(null);

        try {
            const rupees = parseFloat(amount);
            if (!amount || isNaN(rupees) || rupees <= 0) {
                setError("Enter a valid amount greater than ₹0");
                return;
            }

            if (rupees < 1) {
                setError("Minimum payout is ₹1");
                return;
            }

            const paise = Math.round(rupees * 100);

            if (!bankAccountId) {
                setError("Select a bank account");
                return;
            }

            const result = await createPayout(
                merchantId,
                generateIdempotencyKey(),
                { amount_paise: paise, bank_account_id: bankAccountId }
            );
            if (addToast) {
                addToast(`Payout of ₹${rupees.toFixed(2)} created`, "success");
            }
            setAmount("");
            if (onPayoutCreated) onPayoutCreated(result);
        } catch (err) {
            const msg = err.data?.error || err.message || "Failed to create payout";
            setError(msg);
            if (addToast) addToast(msg, "error");
        } finally {
            setSubmitting(false);
            submittingRef.current = false;
        }
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-5">
            <div>
                <label className="block text-xs font-semibold text-gray-400 mb-2">
                    Amount (₹)
                </label>
                <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 text-sm font-semibold">
                        ₹
                    </span>
                    <input
                        type="number"
                        step="0.01"
                        min="1"
                        placeholder="0.00"
                        value={amount}
                        onChange={(e) => {
                            setAmount(e.target.value);
                            setError(null);
                        }}
                        className="input pl-9 text-lg font-semibold"
                        disabled={submitting}
                    />
                </div>
                {amount && !isNaN(parseFloat(amount)) && parseFloat(amount) > 0 && (
                    <p className="text-[11px] text-gray-600 mt-1.5 font-medium">
                        = {Math.round(parseFloat(amount) * 100).toLocaleString("en-IN")} paise
                    </p>
                )}
            </div>

            <div>
                <label className="block text-xs font-semibold text-gray-400 mb-2">
                    Bank Account
                </label>
                <div className="relative">
                    <select
                        value={bankAccountId}
                        onChange={(e) => setBankAccountId(Number(e.target.value))}
                        className="select"
                        disabled={submitting}
                    >
                        {accounts.map((acc) => (
                            <option key={acc.id} value={acc.id}>
                                {acc.label}
                            </option>
                        ))}
                    </select>
                    <svg
                        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
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
                <p className="text-[11px] text-gray-600 mt-1.5 font-medium">
                    {accounts.find((a) => a.id === bankAccountId)?.holder}
                </p>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 fade-in">
                    <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                        </svg>
                        <p className="text-sm text-red-400 font-medium">{error}</p>
                    </div>
                </div>
            )}

            <button
                type="submit"
                disabled={submitting || !amount}
                className="btn-primary w-full flex items-center justify-center gap-2.5"
            >
                {submitting ? (
                    <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Processing...
                    </>
                ) : (
                    <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                        </svg>
                        Request Payout
                    </>
                )}
            </button>
        </form>
    );
}
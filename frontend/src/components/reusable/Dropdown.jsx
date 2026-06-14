import { useState, Fragment } from "react";
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Transition,
} from "@headlessui/react";

export default function Dropdown({
  label,
  value,
  onChange,
  options = [],
  placeholder = "Select an option...",
  searchable = false,
  disabled = false,
  className = "",
}) {
  const [query, setQuery] = useState("");

  // Normalize options to { value, label, icon? } format
  const normalizedOptions = options.map((opt) =>
    typeof opt === "string" ? { value: opt, label: opt } : opt
  );

  // Filter options based on search query
  const filteredOptions =
    searchable && query
      ? normalizedOptions.filter((opt) =>
          opt.label.toLowerCase().includes(query.toLowerCase())
        )
      : normalizedOptions;

  // Find the currently selected option for display
  const selectedOption = normalizedOptions.find((opt) => opt.value === value);

  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-slate-300">
          {label}
        </label>
      )}

      <Listbox value={value} onChange={onChange} disabled={disabled}>
        <div className="relative">
          {/* Trigger Button */}
          <ListboxButton
            className={`group relative w-full cursor-pointer rounded-xl border bg-slate-900/50 py-3 pl-4 pr-10 text-left transition
              focus:outline-none focus:ring-1
              ${
                disabled
                  ? "cursor-not-allowed border-slate-800 opacity-50"
                  : "border-slate-700 hover:border-slate-500 focus:border-cyan-400 focus:ring-cyan-400"
              }
            `}
          >
            <span
              className={`block truncate ${
                selectedOption ? "text-white" : "text-slate-500"
              }`}
            >
              {selectedOption ? (
                <span className="flex items-center gap-2">
                  {selectedOption.icon && <span>{selectedOption.icon}</span>}
                  {selectedOption.label}
                </span>
              ) : (
                placeholder
              )}
            </span>

            {/* Chevron icon */}
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
              <svg
                className="h-4 w-4 text-slate-400 transition-transform duration-200 group-data-[open]:rotate-180"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                  clipRule="evenodd"
                />
              </svg>
            </span>
          </ListboxButton>

          {/* Options Panel */}
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
            enter="transition ease-out duration-150"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            afterLeave={() => setQuery("")}
          >
            <ListboxOptions
              className="absolute z-50 mt-2 max-h-60 w-full overflow-auto rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/40 backdrop-blur-xl
                focus:outline-none"
            >
              {/* Search Input */}
              {searchable && (
                <div className="sticky top-0 z-10 border-b border-slate-700/50 bg-slate-900 p-2">
                  <div className="relative">
                    <svg
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.45 4.39l3.58 3.58a.75.75 0 1 1-1.06 1.06l-3.58-3.58A7 7 0 0 1 2 9Z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <input
                      type="text"
                      className="w-full rounded-lg border border-slate-700 bg-slate-800/50 py-2 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                      placeholder="Search..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      // Prevent Listbox from capturing key events meant for the input
                      onKeyDown={(e) => e.stopPropagation()}
                    />
                  </div>
                </div>
              )}

              {/* Options list */}
              <div className="p-1">
                {filteredOptions.length === 0 ? (
                  <div className="px-4 py-3 text-center text-sm text-slate-500">
                    No results found
                  </div>
                ) : (
                  filteredOptions.map((opt) => (
                    <ListboxOption
                      key={opt.value}
                      value={opt.value}
                      className="group relative cursor-pointer select-none rounded-lg px-4 py-2.5 text-sm text-slate-300 transition
                        data-[focus]:bg-cyan-500/10 data-[focus]:text-cyan-300
                        data-[selected]:font-semibold data-[selected]:text-cyan-300"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 truncate">
                          {opt.icon && <span>{opt.icon}</span>}
                          {opt.label}
                        </span>

                        {/* Checkmark for selected item */}
                        <svg
                          className="hidden h-4 w-4 shrink-0 text-cyan-400 group-data-[selected]:block"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          aria-hidden="true"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </ListboxOption>
                  ))
                )}
              </div>
            </ListboxOptions>
          </Transition>
        </div>
      </Listbox>
    </div>
  );
}
export const CUSTOMIZATION_PRESETS = [
  'No Milk',
  'No Onion',
  'No Garlic',
  'Less Spice',
  'Less Sweet',
  'Extra Vegetables',
];

type CustomizationInputProps = {
  value: string;
  onChange: (value: string) => void;
  id?: string;
  className?: string;
  placeholder?: string;
};

export function CustomizationInput({
  value,
  onChange,
  id = 'customization-presets',
  className = 'form-input w-full mt-1 px-3 py-2 rounded-lg text-sm',
  placeholder = 'Pick a preset or type your own',
}: CustomizationInputProps) {
  return (
    <>
      <input
        type="text"
        list={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={className}
      />
      <datalist id={id}>
        {CUSTOMIZATION_PRESETS.map((preset) => (
          <option key={preset} value={preset} />
        ))}
      </datalist>
    </>
  );
}

"""Compare legacy and renamed primary gemstone labels consistently."""
def matches_condition(field_name, value, expected):
    def normalize(entry):
        result = str(entry or '').strip().lower()
        if field_name == 'primary_gemstone':
            result = ' '.join(result.split())
            if result == 'natural diamonds':
                result = 'natural diamond'
        return result
    return normalize(value) == normalize(expected)

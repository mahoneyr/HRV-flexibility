# Contributing to Autonomic Flexibility Analyzer

Thank you for your interest in contributing! This is a collaborative research project, and contributions are welcome.

## How to Contribute

### Bug Reports
If you find a bug:
1. **Check if it's already reported** in the Issues section
2. **Create a new issue** with:
   - A clear description of the bug
   - Steps to reproduce
   - Your CSV data format (anonymized if needed)
   - Expected vs. actual behavior
   - Your system info (OS, Python version, Docker version)

### Feature Suggestions
Have an idea to improve the analyzer?
1. **Open an issue** with label `enhancement`
2. **Describe** what you'd like to add and why
3. **Discuss** before implementing to ensure alignment

### Scientific Feedback
If you have feedback on the HRV algorithms:
1. **Open an issue** with label `scientific-discussion`
2. **Share** your insights, concerns, or references
3. **Be respectful** and cite relevant literature

### Code Contributions
Want to submit code? Great!

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/your-feature-name`
3. **Make your changes** with clear, atomic commits
4. **Add or update tests** if applicable
5. **Update documentation** if your changes affect the README or usage
6. **Submit a pull request** with:
   - Clear description of what you changed and why
   - Reference to any related issues
   - Screenshots/videos if it's a UI change

## Contribution Guidelines

- **Keep it focused:** One feature or fix per PR when possible
- **Test your changes:** Ensure the app still works with your modifications
- **Follow existing code style:** Match the patterns already in the codebase
- **No breaking changes** to the data format without discussion
- **Respect the GPL v3 license:** All contributions must be compatible

## Development Setup

### Clone and Setup
```bash
git clone https://github.com/mahoneyr/HRV-flexibility.git
cd HRV-flexibility
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Without Docker
```bash
python app.py
```
The app will be available at `http://localhost:5000`

### Testing Your Changes
1. Upload test CSV files to verify functionality
2. Check both dual-file and auto-split modes
3. Verify the 12-state classification logic
4. Test with different data scenarios (short sessions, noisy data, etc.)

## Areas We're Looking For Help

- 🐛 **Bug fixes** — Any issues you find
- 📊 **Data format improvements** — Better support for different HRV devices
- 🧬 **Algorithm validation** — Scientific review of DFA and RMSSD calculations
- 📱 **UI/UX improvements** — Better charts, clearer results display
- 📚 **Documentation** — Clearer guides, example datasets
- 🐳 **Docker improvements** — Better container setup, multi-platform support
- 🧪 **Unit tests** — More test coverage for edge cases

## Community Standards

- **Be respectful** and constructive
- **Listen to feedback** and be open to discussion
- **Credit others** when building on their work
- **Avoid** political, promotional, or off-topic discussions

## License

All contributions must be compatible with GPL v3. By submitting code, you agree to license it under GPL v3.

## Questions?

Open an issue with your question! We're here to help.

---

Thank you for contributing to better HRV analysis for everyone! 🙌

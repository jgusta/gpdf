class Gpdf < Formula
  desc "grep-like search for PDFs"
  homepage "https://github.com/jgusta/gpdf"
  version "0.1.2"

  if OS.mac?
    url "https://github.com/jgusta/gpdf/releases/download/v#{version}/gpdf-macos-latest"
    sha256 "68af122fd35a1459060746f7159cc270e8b87a111e4b0fbe754b6f9917b9603b"
  elsif OS.linux?
    url "https://github.com/jgusta/gpdf/releases/download/v#{version}/gpdf-ubuntu-latest"
    sha256 "417b8fbd4accad75483a2297ed5c8005aa9f5bda632a3794d146bd4dedc887e3"
  end

  def install
    bin.install Dir["gpdf-*"].first => "gpdf"
  end
end

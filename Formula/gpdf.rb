class Gpdf < Formula
  desc "grep-like search for PDFs"
  homepage "https://github.com/jgusta/gpdf"
  version "0.1.0"

  if OS.mac?
    url "https://github.com/jgusta/gpdf/releases/download/v#{version}/gpdf-macos-latest"
    sha256 "REPLACE_WITH_SHA256_FOR_MACOS"
  elsif OS.linux?
    url "https://github.com/jgusta/gpdf/releases/download/v#{version}/gpdf-ubuntu-latest"
    sha256 "REPLACE_WITH_SHA256_FOR_LINUX"
  end

  def install
    bin.install Dir["gpdf-*"].first => "gpdf"
  end
end

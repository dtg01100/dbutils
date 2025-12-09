class Dbutils < Formula
  include Language::Python::Virtualenv

  desc "Utilities to discover and reason about database schemas via JDBC"
  homepage "https://github.com/dtg01100/dbutils"
  url "https://github.com/dtg01100/dbutils/archive/v0.1.0.tar.gz"
  sha256 "ab8466e147e9d9c668bb983696d1ab98943c53b7e7d65dc552bbe46d3037770c"
  license "MIT"

  depends_on "python@3.13"

  def install
    # Install the package and its dependencies using virtualenv
    virtualenv_install_with_resources
  end

  test do
    # Basic smoke test to ensure the package is installed
    system "#{libexec}/bin/python", "-c", "import dbutils; print('dbutils installed')"
  end
end

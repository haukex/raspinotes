#!/usr/bin/perl
use warnings;
use 5.014;  # strict, HTTP::Tiny, JSON::PP
# should run on vanilla Perl, use core modules only
use Sys::Hostname 'hostname';
use Digest::SHA 'hmac_sha256_base64';
use JSON::PP ();
use HTTP::Tiny ();

my $SECRET = 'secret';  # FIXME: CHANGE THIS - for signature, so server can verify authenticity
my $URL = 'https://example.com/hellorpi';

# IPv4 only at the moment:
my @ips = sort grep { /\A\d+(?:\.\d+){3}\z/ } split ' ', `/usr/bin/hostname -I`;
die "`hostname -I` failed with \$?=$?\n" if $?;
exit unless @ips;

my $host = hostname;
die "unexpected hostname '$host'\n" unless $host=~/\A[A-Za-z0-9\.\-\_]+\z/;

my $sig = hmac_sha256_base64(join("\0", $host, @ips), $SECRET);
$sig .= '=' while length($sig) % 4;  # pad

my $resp = HTTP::Tiny->new->request('POST', $URL, { content=>
    JSON::PP->new->ascii->canonical->pretty->encode(
        { host => $host, ips => \@ips, sig => $sig }) });
die "POST $URL => $resp->{status} $resp->{reason}\n" unless $resp->{success};

# spell: ignore hmac
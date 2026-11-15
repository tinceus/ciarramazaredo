/* Everything that waits on Ciarra lives here. Empty values keep their section hidden.
   Fill a value, push, and the matching part of the site appears. */
window.SITE = {
  sprintBookingUrl: null,   // HTTPS fit-call URL, separate from general booking
  newsletterUrl: null,      // Optional explicit-consent signup page
  storefrontUrl: null,      // Set only after product release gates pass
  bookingUrl: null,          // NeetoCal link, for example "https://ciarra.neetocal.com/intro-call"
  introVideoId: null,        // YouTube video id of the 60 to 90 second introduction
  remote: {
    hoursOverlap: null,      // for example "Full US Eastern business hours"
    employmentType: null,    // for example "Full-time, long-term"
    setup: null              // for example "Home office, fiber internet with backup"
  }
};
